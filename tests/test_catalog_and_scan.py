"""Tests for the catalog metadata rendering and the scan gate."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"


def _run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=120,
    )


def test_render_catalog_metadata_requires_a_real_sha(tmp_path: Path):
    result = _run(
        "render_catalog_metadata.py",
        "--image",
        "does-not-matter:latest",
        "--source-sha",
        "not-a-sha",
        "--version",
        "3.0.1",
        "--output-dir",
        str(tmp_path),
    )
    assert result.returncode != 0
    assert "40-character" in result.stderr


def test_render_catalog_metadata_rejects_unpublished_images(tmp_path: Path):
    result = _run(
        "render_catalog_metadata.py",
        "--image",
        "percival-deep-research:never-pushed",
        "--source-sha",
        "a" * 40,
        "--version",
        "3.0.1",
        "--output-dir",
        str(tmp_path),
    )
    assert result.returncode != 0
    assert "RepoDigest" in result.stderr or "no RepoDigest" in result.stderr


def test_scan_gate_reports_unrecorded_findings(tmp_path: Path):
    report = {
        "Results": [
            {
                "Vulnerabilities": [
                    {"VulnerabilityID": "CVE-1111-2222"},
                    {"VulnerabilityID": "CVE-3333-4444"},
                ]
            }
        ]
    }
    report_path = tmp_path / "trivy.json"
    report_path.write_text(json.dumps(report))

    vex_path = tmp_path / "vex.json"
    vex_path.write_text(
        json.dumps(
            {
                "statements": [
                    {"vulnerability": {"name": "CVE-1111-2222"}},
                ]
            }
        )
    )

    result = _run(
        "check_trivy_findings.py",
        "--report",
        str(report_path),
        "--known",
        str(vex_path),
    )
    assert result.returncode == 1
    assert "CVE-3333-4444" in result.stderr
    assert "CVE-1111-2222" not in result.stderr


def test_scan_gate_accepts_recorded_findings(tmp_path: Path):
    report = {"Results": [{"Vulnerabilities": [{"VulnerabilityID": "CVE-1111-2222"}]}]}
    report_path = tmp_path / "trivy.json"
    report_path.write_text(json.dumps(report))

    vex_path = tmp_path / "vex.json"
    vex_path.write_text(json.dumps({"statements": [{"vulnerability": {"name": "CVE-1111-2222"}}]}))

    result = _run(
        "check_trivy_findings.py",
        "--report",
        str(report_path),
        "--known",
        str(vex_path),
    )
    assert result.returncode == 0


@pytest.mark.skipif(
    not (PROJECT_ROOT / "docs" / "security" / "vex-2026-10-28.json").exists(),
    reason="no VEX document recorded",
)
def test_recorded_vex_covers_every_statement_with_a_decision():
    vex = json.loads((PROJECT_ROOT / "docs" / "security" / "vex-2026-10-28.json").read_text())
    statements = vex["statements"]
    assert statements, "the VEX document must record the open findings"
    for statement in statements:
        assert statement["vulnerability"]["name"]
        assert statement["status"] == "under_investigation", (
            "an open finding must not be declared resolved without an upgrade"
        )
        assert statement["justification"].strip(), (
            "every statement needs the owner decision that justifies it"
        )
        assert statement["products"], "every statement must name the affected product"
