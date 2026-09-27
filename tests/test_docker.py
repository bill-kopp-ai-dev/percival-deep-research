"""Static regression tests for Docker packaging.

These tests do NOT spawn containers — they verify the Dockerfile,
.dockerignore, and docker-compose.yml have the required structure for
compatibility with Nanobot, OpenCode, and the Docker MCP gateway.

For a full container smoke test (boot + JSON-RPC initialize + /health),
run ``scripts/docker_smoke_test.sh`` manually.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = PROJECT_ROOT / "Dockerfile"
DOCKERIGNORE = PROJECT_ROOT / ".dockerignore"
DOCKER_COMPOSE = PROJECT_ROOT / "docker-compose.yml"
DOCKER_DIR = PROJECT_ROOT / "docker"


# ─────────────────────────────────────────────────────────────────────
# .dockerignore
# ─────────────────────────────────────────────────────────────────────


class TestDockerignore:
    """Verifies .dockerignore is present and excludes dangerous paths."""

    @pytest.fixture
    def lines(self) -> list[str]:
        assert DOCKERIGNORE.exists(), (
            ".dockerignore must exist — otherwise the build context ships "
            ".venv, .env, and .git into the image, overwriting the venv we "
            "just built and leaking secrets."
        )
        return DOCKERIGNORE.read_text().splitlines()

    def test_excludes_venv(self, lines: list[str]) -> None:
        assert any(".venv" in ln for ln in lines), (
            ".venv must be excluded — the host venv would overwrite the "
            "image's freshly built venv and break the build."
        )

    def test_excludes_git(self, lines: list[str]) -> None:
        assert any(ln.strip() in (".git", ".git/") for ln in lines), (
            ".git must be excluded from the build context."
        )

    def test_excludes_dotenv_but_keeps_example(self, lines: list[str]) -> None:
        stripped = [ln.strip() for ln in lines]
        # `.env` (the actual secrets file) must be excluded.
        assert ".env" in stripped, ".env must be excluded to avoid leaking secrets into the image."
        # `.env.example` must be re-included (the template travels with us).
        assert any(ln == "!.env.example" for ln in stripped), (
            ".env.example must be re-included (negation pattern)."
        )

    def test_excludes_pycache(self, lines: list[str]) -> None:
        assert any("__pycache__" in ln for ln in lines), (
            "__pycache__ must be excluded from the build context."
        )

    def test_excludes_coverage(self, lines: list[str]) -> None:
        assert any(".coverage" in ln for ln in lines), (
            ".coverage artifacts must be excluded from the build context."
        )

    def test_excludes_pytest_cache(self, lines: list[str]) -> None:
        assert any(".pytest_cache" in ln for ln in lines), (
            ".pytest_cache must be excluded from the build context."
        )

    def test_excludes_ruff_cache(self, lines: list[str]) -> None:
        assert any(".ruff_cache" in ln for ln in lines), (
            ".ruff_cache must be excluded from the build context."
        )

    def test_excludes_logs(self, lines: list[str]) -> None:
        assert any(ln.strip().rstrip("/") == "logs" for ln in lines), (
            "logs/ must be excluded — runtime logs belong to the host, not the image."
        )


# ─────────────────────────────────────────────────────────────────────
# Dockerfile
# ─────────────────────────────────────────────────────────────────────


class TestDockerfile:
    """Verifies Dockerfile structure for MCP client compatibility."""

    @pytest.fixture
    def contents(self) -> str:
        assert DOCKERFILE.exists(), "Dockerfile must exist"
        return DOCKERFILE.read_text()

    def test_uses_uv_base_image(self, contents: str) -> None:
        # Either base image or `COPY --from=ghcr.io/astral-sh/uv`.
        assert "ghcr.io/astral-sh/uv" in contents, (
            "Dockerfile must reference `ghcr.io/astral-sh/uv` for "
            "reproducible dependency installation."
        )

    def test_has_oci_labels(self, contents: str) -> None:
        for label in (
            "org.opencontainers.image.title",
            "org.opencontainers.image.source",
            "org.opencontainers.image.licenses",
            "org.opencontainers.image.version",
        ):
            assert label in contents, (
                f"OCI label `{label}` is required for the Docker MCP catalog "
                f"and for `docker inspect` discoverability."
            )

    def test_has_mcp_label(self, contents: str) -> None:
        # MCP-specific label for Docker MCP Toolkit / catalog discovery.
        assert "io.modelcontextprotocol.server.name" in contents, (
            "`io.modelcontextprotocol.server.name` is required so that "
            "the Docker MCP gateway and catalog can identify this image "
            "as an MCP server."
        )

    def test_mcp_server_name_label_value(self, contents: str) -> None:
        # The label value must be a non-empty quoted string.
        m = re.search(r'io\.modelcontextprotocol\.server\.name="([^"]+)"', contents)
        assert m and m.group(1).strip(), (
            "`io.modelcontextprotocol.server.name` must have a non-empty "
            "value (e.g. `percival-deep-research`)."
        )

    def test_applies_gpt_researcher_patch(self, contents: str) -> None:
        # The patch must run inside the BUILD, not runtime — otherwise
        # the container crashes on first import with `NameError: name 'Any'`.
        assert "patch_gpt_researcher.py" in contents, (
            "Dockerfile must apply `scripts/patch_gpt_researcher.py` "
            "during the build — without it, `gpt-researcher >= 0.16.0` "
            "crashes on import with NameError."
        )

    def test_disables_bytecode_compilation(self, contents: str) -> None:
        # UV_COMPILE_BYTECODE=1 + PYTHONDONTWRITEBYTECODE=1 would conflict
        # and bake ~120 MB of .pyc files into the venv. We rely on
        # PYTHONDONTWRITEBYTECODE alone (uv respects it when
        # UV_COMPILE_BYTECODE is unset).
        compile_set = re.search(r"UV_COMPILE_BYTECODE\s*=\s*1", contents)
        assert not compile_set, (
            "Dockerfile must NOT set UV_COMPILE_BYTECODE=1 — it conflicts "
            "with PYTHONDONTWRITEBYTECODE=1 and bakes ~120 MB of .pyc files "
            "into the venv. Just set PYTHONDONTWRITEBYTECODE=1."
        )
        # PYTHONDONTWRITEBYTECODE must be set somewhere (builder or runtime).
        assert "PYTHONDONTWRITEBYTECODE" in contents, (
            "Dockerfile must set PYTHONDONTWRITEBYTECODE=1 to avoid .pyc bloat in the image."
        )

    def test_strips_package_bloat(self, contents: str) -> None:
        # The cleanup step removes tests/, *.pyi, and *.dist-info/RECORD.
        # Asserts all three categories are covered.
        for token, rationale in (
            ("tests", "removes ~49 MB of tests/ directories from packages"),
            ("*.pyi", "removes ~2.7 MB of type stubs (.pyi files)"),
            ("RECORD", "removes pip's RECORD files (uninstall bookkeeping)"),
        ):
            assert token in contents, (
                f"Dockerfile cleanup step must handle `{token}` — {rationale}."
            )

    def test_runs_as_non_root(self, contents: str) -> None:
        # USER directive must be present (and not be `USER root`).
        user_lines = [ln.strip() for ln in contents.splitlines() if ln.strip().startswith("USER ")]
        assert user_lines, (
            "Dockerfile must set `USER` to a non-root user — running as "
            "root is a hardening regression for MCP servers handling "
            "untrusted web content."
        )
        last_user = user_lines[-1]
        # Strip trailing comments for the comparison.
        last_user_token = last_user.split("#", 1)[0].strip().split()[-1]
        assert last_user_token != "root", (
            f"Dockerfile must not run as root. Last USER directive: {last_user!r}"
        )

    def test_user_uid_at_least_1000(self, contents: str) -> None:
        # Prefer UID >= 1000 to match the nanobot convention and avoid
        # conflicting with host UIDs on volume mounts.
        m = re.search(r"useradd[^|\\n]*--uid\s+(\d+)", contents)
        assert m, "useradd should use an explicit --uid"
        uid = int(m.group(1))
        assert uid >= 1000, (
            f"useradd UID should be >= 1000 (host-UID collision avoidance). Got: {uid}"
        )

    def test_entrypoint_is_exec_form(self, contents: str) -> None:
        # ENTRYPOINT must be JSON array form for proper signal handling.
        ep_match = re.search(r"^ENTRYPOINT\s+(.+)$", contents, re.MULTILINE)
        assert ep_match, "ENTRYPOINT must be set"
        ep_value = ep_match.group(1).strip()
        assert ep_value.startswith("[") and ep_value.endswith("]"), (
            f"ENTRYPOINT must use exec form (JSON array). Got: {ep_value!r}"
        )

    def test_default_transport_is_stdio(self, contents: str) -> None:
        # Default transport must be stdio for Nanobot / OpenCode / Docker MCP gateway.
        m = re.search(r"^\s*MCP_TRANSPORT=(\S+)", contents, re.MULTILINE)
        assert m, "MCP_TRANSPORT default must be set"
        assert m.group(1).strip().lower() == "stdio", (
            f"MCP_TRANSPORT default must be `stdio` for MCP client compatibility. "
            f"Got: {m.group(1)!r}"
        )

    def test_healthcheck_present(self, contents: str) -> None:
        assert "HEALTHCHECK" in contents, (
            "Dockerfile must include a HEALTHCHECK directive for SSE/HTTP mode."
        )

    def test_exposes_8000(self, contents: str) -> None:
        assert re.search(r"^EXPOSE\s+8000\b", contents, re.MULTILINE), (
            "Dockerfile must EXPOSE 8000 (the SSE/HTTP mode port)."
        )

    def test_uses_tini_for_signal_forwarding(self, contents: str) -> None:
        # tini as PID 1 (or ENTRYPOINT) ensures SIGTERM reaches the Python process.
        assert re.search(r"\btini\b", contents), (
            "Dockerfile should use `tini` for proper signal forwarding "
            "(PID 1 zombie reaping + SIGTERM to the MCP server)."
        )


# ─────────────────────────────────────────────────────────────────────
# server.py — no auto-switch to SSE inside Docker
# ─────────────────────────────────────────────────────────────────────


class TestServerNoAutoSwitch:
    """The Docker auto-switch to SSE was removed because it broke stdio-based
    MCP clients (Nanobot, OpenCode, Docker MCP gateway)."""

    def test_server_has_no_docker_sse_autoswitch(self) -> None:
        server_py = PROJECT_ROOT / "server.py"
        assert server_py.exists()
        text = server_py.read_text()
        # The old auto-switch had the shape:
        #   if os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER"):
        #       transport = "sse"
        forbidden = re.search(
            r'os\.path\.exists\([^)]*dockerenv[^)]*\)\s*or\s*os\.getenv\(\s*"DOCKER_CONTAINER"\s*\)',
            text,
        )
        assert not forbidden, (
            "server.py must NOT auto-switch transport based on "
            "`/.dockerenv` or `DOCKER_CONTAINER` — this broke stdio-based "
            "MCP clients (Nanobot, OpenCode, Docker MCP gateway). Operators "
            "should set `MCP_TRANSPORT` explicitly when they want HTTP."
        )


# ─────────────────────────────────────────────────────────────────────
# docker-compose.yml
# ─────────────────────────────────────────────────────────────────────


class TestDockerCompose:
    """Compose file hygiene."""

    @pytest.fixture
    def contents(self) -> str:
        assert DOCKER_COMPOSE.exists()
        return DOCKER_COMPOSE.read_text()

    def test_no_obsolete_version_key(self, contents: str) -> None:
        # Compose v2 ignores `version:` — its presence is a smell.
        assert not re.search(r"^version:\s*['\"]", contents, re.MULTILINE), (
            "docker-compose.yml must not have a top-level `version:` key — "
            "Compose v2 ignores it and its presence is obsolete."
        )

    def test_stdin_and_tty_enabled(self, contents: str) -> None:
        # Required for `docker compose run` with stdio transport.
        assert "stdin_open: true" in contents, (
            "stdin_open: true is required for stdio MCP transport via `docker compose run`."
        )
        assert "tty: true" in contents, (
            "tty: true is required for clean signal handling in stdio mode."
        )

    def test_env_file_is_optional(self, contents: str) -> None:
        # `required: false` means operators without a .env file still work.
        assert re.search(r"required:\s*false", contents), (
            "env_file must be marked `required: false` so that operators "
            "who use env vars directly (or a secrets manager) don't fail "
            "to bring up the container."
        )

    def test_default_retriever_aligns_with_env_example(self, contents: str) -> None:
        # The compose env must not default to brave — that contradicts
        # `.env.example` (default = duckduckgo, v3.0+) and silently
        # requires BRAVE_API_KEY.
        m = re.search(r"RETRIEVER[^\n]*\$\{RETRIEVER:-([^}]+)\}", contents)
        assert m, "compose should set RETRIEVER with a default"
        default = m.group(1).strip()
        assert default.lower() != "brave", (
            f"compose default for RETRIEVER must not be brave. Got: {default!r}"
        )


# ─────────────────────────────────────────────────────────────────────
# Docker MCP catalog metadata
# ─────────────────────────────────────────────────────────────────────


class TestDockerCatalogMetadata:
    """Optional metadata for submitting to docker/mcp-registry."""

    @classmethod
    @pytest.fixture(scope="class")
    def server_yaml(cls) -> Path:
        p = DOCKER_DIR / "server.yaml"
        if not p.exists():
            pytest.skip("docker/server.yaml not present — catalog submission optional")
        return p

    @classmethod
    @pytest.fixture(scope="class")
    def tools_json(cls) -> Path:
        p = DOCKER_DIR / "tools.json"
        if not p.exists():
            pytest.skip("docker/tools.json not present — catalog submission optional")
        return p

    def test_server_yaml_has_required_top_level_fields(self, server_yaml: Path) -> None:
        text = server_yaml.read_text()
        for field in ("name:", "image:", "type: server", "about:", "config:"):
            assert field in text, (
                f"docker/server.yaml must contain `{field}` for catalog "
                f"submission. See docker/mcp-registry CONTRIBUTING.md."
            )

    def test_server_yaml_declares_required_secrets(self, server_yaml: Path) -> None:
        text = server_yaml.read_text()
        # INFERENCE_API_KEY must be declared as a secret for the catalog UI.
        assert "INFERENCE_API_KEY" in text, (
            "INFERENCE_API_KEY must be declared in `config.secrets` so the "
            "Docker MCP Toolkit can prompt for it."
        )

    def test_tools_json_is_valid_and_has_five_tools(self, tools_json: Path) -> None:
        tools = json.loads(tools_json.read_text())
        assert isinstance(tools, list) and tools, "tools.json must be a non-empty JSON array"
        names = {t["name"] for t in tools}
        expected = {
            "research_deep",
            "research_quick_search",
            "research_get_context",
            "research_get_sources",
            "research_write_report",
        }
        missing = expected - names
        assert not missing, (
            f"tools.json must declare all 5 public tools. Missing: {sorted(missing)}"
        )
        for tool in tools:
            assert "name" in tool and "description" in tool, (
                f"tool entry must have `name` and `description`: {tool!r}"
            )

    def test_tools_json_signatures_match_actual_functions(self, tools_json: Path) -> None:
        """Regression: docker/tools.json argument names MUST match the actual
        tool function signatures. If someone changes a parameter name in the
        function but forgets to update tools.json, the Docker MCP catalog
        would advertise a non-working interface.

        This test inspects the actual tool handlers and verifies each
        argument declared in tools.json is a real parameter (and vice versa).
        """
        import inspect

        # Map tool name -> actual async function. The functions are imported
        # from the same modules that register them via @mcp.tool(name=...).
        tool_modules = {
            "research_deep": "percival_research.tools.deep_research",
            "research_quick_search": "percival_research.tools.quick_search",
            "research_get_context": "percival_research.tools.get_research_context",
            "research_get_sources": "percival_research.tools.get_research_sources",
            "research_write_report": "percival_research.tools.write_report",
        }
        function_names = {
            "research_deep": "deep_research",
            "research_quick_search": "quick_search",
            "research_get_context": "get_research_context",
            "research_get_sources": "get_research_sources",
            "research_write_report": "write_report",
        }

        tools = json.loads(tools_json.read_text())
        for tool in tools:
            name = tool["name"]
            module = tool_modules[name]
            func_name = function_names[name]
            func = getattr(__import__(module, fromlist=[func_name]), func_name)
            sig = inspect.signature(func)
            actual_params = set(sig.parameters)
            declared_args = {a["name"] for a in tool.get("arguments", [])}

            missing_in_json = actual_params - declared_args
            extra_in_json = declared_args - actual_params
            assert not missing_in_json, (
                f"tools.json entry for `{name}` is missing arguments that "
                f"the real function declares: {sorted(missing_in_json)}"
            )
            assert not extra_in_json, (
                f"tools.json entry for `{name}` declares arguments the real "
                f"function does NOT accept (will fail at runtime): "
                f"{sorted(extra_in_json)}"
            )
