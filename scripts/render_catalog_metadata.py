#!/usr/bin/env python3
"""Render the catalog metadata for the current release.

The Docker MCP Registry requires `servers/<name>/server.yaml` to pin the
audited revision in `source.commit` (a 40-character lowercase SHA1), and
the MCP registry `server.json` to carry the published image digest.

Both values are known only when the release is cut, so they are rendered
from the git checkout and the built image instead of being committed as
stale literals.

Usage:
    scripts/render_catalog_metadata.py \
        --image percival-deep-research:3.0.1 \
        --source-sha "$(git rev-parse HEAD)" \
        --output-dir docker
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
PLACEHOLDER = "PLACEHOLDER_RELEASE_COMMIT_SHA"
DIGEST_PLACEHOLDER = "PLACEHOLDER_RELEASE_IMAGE_DIGEST"


def image_digest(image: str) -> str:
    """Return the RepoDigest of a published image (sha256:<hex>)."""
    raw = subprocess.check_output(
        ["docker", "image", "inspect", image, "--format", "{{json .RepoDigests}}"],
        text=True,
    )
    digests = json.loads(raw)
    if not digests:
        raise SystemExit(f"image {image} has no RepoDigest: it was never pushed to a registry")
    return digests[0]


def render_server_yaml(path: Path, source_sha: str, version: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"^(\s*commit:)\s*\S+\s*$",
        rf"\1 {source_sha}",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^(\s*version:)\s*\S+\s*$",
        rf"\1 {version}",
        text,
        flags=re.MULTILINE,
    )
    path.write_text(text, encoding="utf-8")


def render_server_json(path: Path, source_sha: str, digest: str, version: str) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["version"] = version
    for package in payload.get("packages", []):
        package["version"] = version
        if package.get("registryType") == "oci":
            package["identifier"] = f"docker.io/mcp/percival-deep-research:{version}"
    publisher = payload.get("_meta", {}).get(
        "io.modelcontextprotocol.registry/publisher-provided", {}
    )
    build_info = publisher.setdefault("build_info", {})
    build_info["source_commit"] = source_sha
    build_info["image_digest"] = digest
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="published image to read the digest from")
    parser.add_argument("--source-sha", required=True, help="40-character commit SHA")
    parser.add_argument("--version", required=True, help="released product version")
    parser.add_argument("--output-dir", type=Path, default=Path("docker"))
    args = parser.parse_args()

    if SHA1_RE.match(args.source_sha) is None:
        raise SystemExit("--source-sha must be a 40-character lowercase SHA1")

    digest = image_digest(args.image)
    render_server_yaml(args.output_dir / "server.yaml", args.source_sha, args.version)
    render_server_json(args.output_dir / "server.json", args.source_sha, digest, args.version)
    print(f"catalog metadata rendered: commit={args.source_sha} digest={digest}")


if __name__ == "__main__":
    raise SystemExit(main())
