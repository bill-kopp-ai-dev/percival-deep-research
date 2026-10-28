#!/usr/bin/env python3
"""Fail when the image scan reports a vulnerability that is not on record.

The known findings are declared in an OpenVEX document under
`docs/security/`. Every vulnerability the scanner reports must appear
there with an owner decision, so a newly published advisory cannot pass
through CI unnoticed.

Usage:
    scripts/check_trivy_findings.py --report trivy.json --known docs/security/vex-2026-10-28.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def reported_ids(report: dict) -> set[str]:
    found: set[str] = set()
    for result in report.get("Results", []) or []:
        for vulnerability in result.get("Vulnerabilities", []) or []:
            identifier = vulnerability.get("VulnerabilityID")
            if identifier:
                found.add(identifier)
    return found


def known_ids(vex: dict) -> set[str]:
    known: set[str] = set()
    for statement in vex.get("statements", []) or []:
        name = (statement.get("vulnerability") or {}).get("name")
        if name:
            known.add(name)
    return known


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True, help="Trivy JSON report")
    parser.add_argument("--known", type=Path, required=True, help="OpenVEX document")
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    vex = json.loads(args.known.read_text(encoding="utf-8"))

    found = reported_ids(report)
    known = known_ids(vex)

    unrecorded = sorted(found - known)
    if unrecorded:
        print(
            "Unrecorded vulnerabilities found by the scan: " + ", ".join(unrecorded),
            file=sys.stderr,
        )
        print(
            "Add each one to the VEX document with an owner decision before merging.",
            file=sys.stderr,
        )
        return 1

    print(f"scan findings recorded: {len(found)} known vulnerabilities, none unrecorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
