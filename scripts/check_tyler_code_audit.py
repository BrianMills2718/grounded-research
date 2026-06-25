"""Audit current-code evidence for Tyler requirement rows.

Traceability rows can look closed because they contain historical prose. This
script checks the current parsed evidence instead: non-doc Tyler rows must cite
current implementation evidence and current verification evidence, or be an
explicit ambiguity/extension/doc-governance row handled by the coverage report.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_tyler_coverage import build_coverage_report  # noqa: E402

SKIPPED_CLASSES = {"ambiguity", "doc_status", "extension"}
IMPLEMENTATION_KINDS = {
    "config",
    "local_source",
    "prompt_template",
    "runtime_artifact",
    "shared_infra_source",
}
VERIFICATION_KINDS = {"local_test", "runtime_artifact", "shared_infra_test"}


@dataclass(frozen=True)
class CodeAuditFinding:
    """One current-code evidence gap for a Tyler requirement row."""

    requirement_id: str
    finding: str
    message: str


def _evidence_kinds(requirement: dict[str, Any]) -> set[str]:
    """Return evidence kinds attached to a coverage requirement row."""

    return {item["kind"] for item in requirement["evidence"]}


def _audit_requirement(requirement: dict[str, Any]) -> list[CodeAuditFinding]:
    """Audit one coverage requirement for current implementation/test evidence."""

    requirement_id = requirement["requirement_id"]
    requirement_class = requirement["requirement_class"]
    if requirement_class in SKIPPED_CLASSES:
        return []

    kinds = _evidence_kinds(requirement)
    findings: list[CodeAuditFinding] = []
    if not (kinds & IMPLEMENTATION_KINDS):
        findings.append(
            CodeAuditFinding(
                requirement_id=requirement_id,
                finding="missing_current_implementation_evidence",
                message="Non-doc Tyler rows need current source, config, prompt, shared-infra, or runtime-artifact evidence.",
            )
        )
    if not (kinds & VERIFICATION_KINDS):
        findings.append(
            CodeAuditFinding(
                requirement_id=requirement_id,
                finding="missing_current_verification_evidence",
                message="Non-doc Tyler rows need current local test, shared-infra test, or runtime-artifact evidence.",
            )
        )
    return findings


def build_code_audit_report() -> dict[str, Any]:
    """Build a current-code evidence audit over the Tyler coverage report."""

    coverage = build_coverage_report()
    audited = [
        row
        for row in coverage["requirements"]
        if row["requirement_class"] not in SKIPPED_CLASSES
    ]
    findings = [finding for row in audited for finding in _audit_requirement(row)]
    return {
        "sources": [
            "docs/TYLER_SPEC_GAP_LEDGER.md",
            "scripts/check_tyler_coverage.py",
        ],
        "summary": {
            "requirements": len(coverage["requirements"]),
            "current_code_audited": len(audited),
            "skipped_doc_or_exception_rows": len(coverage["requirements"]) - len(audited),
            "findings": len(findings),
        },
        "findings": [finding.__dict__ for finding in findings],
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render a maintainer-readable current-code audit."""

    lines = [
        "# Tyler Current-Code Audit",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ]
    for key, value in report["summary"].items():
        lines.append(f"| {key} | {value} |")

    lines.extend(["", "## Findings", ""])
    if report["findings"]:
        for finding in report["findings"]:
            lines.append(
                "- `{requirement_id}` `{finding}`: {message}".format(**finding)
            )
    else:
        lines.append("No current-code evidence gaps found.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """Run the Tyler current-code audit CLI."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args()

    report = build_code_audit_report()
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report))
    if args.fail_on_findings and report["findings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
