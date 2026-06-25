"""Detect stale Tyler status claims on active maintainer-facing docs.

This checker is intentionally narrow. It does not scan archive plans, because
historical documents should preserve the claims that were true when they were
written. The goal is to keep active docs from contradicting the current Tyler
ledger/status surface after remediation work lands.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

ACTIVE_DOCS = (
    Path("README.md"),
    *sorted(Path("docs").glob("*.md")),
    *sorted(path for path in Path("docs/plans").glob("*.md") if path.name != "CLAUDE.md"),
)


@dataclass(frozen=True)
class DriftRule:
    """One active-doc rule that catches a stale Tyler status claim."""

    rule_id: str
    pattern: str
    message: str


@dataclass(frozen=True)
class DriftFinding:
    """One matched stale-doc finding with enough location to fix it."""

    rule_id: str
    path: str
    line: int
    message: str
    excerpt: str


FORBIDDEN_RULES = (
    DriftRule(
        rule_id="stage2_query_model_call",
        pattern=r"Stage 2[^.\n|]*structured model call",
        message="Stage 2 query generation is deterministic Tyler string/template orchestration, not an LLM model call.",
    ),
    DriftRule(
        rule_id="gemini_exact_gap_open",
        pattern=r"exact Gemini 3\.1 Pro model-version row still open|remaining exact(?:-model)? gap.*Gemini|Gemini 2\.5 Pro as a temporary substitute",
        message="Exact Gemini 3.1 Pro preview parity is closed; only the separate frontier runtime watch remains.",
    ),
    DriftRule(
        rule_id="prompt_count_stale",
        pattern=r"\b9 YAML prompt templates\b",
        message="The live prompts directory currently contains 8 YAML prompt templates.",
    ),
)

REQUIRED_PATTERNS = {
    "README.md": (
        r"exact Gemini 3\.1 Pro preview\s+model-version parity is closed",
        r"separate frontier runtime watch",
    ),
    "docs/FEATURE_STATUS.md": (
        r"deterministic Tyler string/orchestrator templates",
        r"Exact Gemini model-version parity is closed",
    ),
    "docs/ROADMAP.md": (
        r"deterministic Tyler orchestrator templates",
        r"exact Gemini model-version parity is closed",
    ),
}


def _iter_active_docs() -> list[Path]:
    """Return tracked active docs that exist in this checkout."""

    return [path for path in ACTIVE_DOCS if (ROOT / path).exists()]


def _find_forbidden_claims(paths: list[Path]) -> list[DriftFinding]:
    """Find stale phrases on active docs."""

    findings: list[DriftFinding] = []
    compiled = [
        (
            rule,
            re.compile(rule.pattern, flags=re.IGNORECASE),
        )
        for rule in FORBIDDEN_RULES
    ]
    for path in paths:
        text = (ROOT / path).read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for rule, pattern in compiled:
                if pattern.search(line):
                    findings.append(
                        DriftFinding(
                            rule_id=rule.rule_id,
                            path=str(path),
                            line=line_number,
                            message=rule.message,
                            excerpt=line.strip(),
                        )
                    )
    return findings


def _missing_required_claims() -> list[DriftFinding]:
    """Ensure key active docs carry the current Tyler status wording."""

    findings: list[DriftFinding] = []
    for path_text, patterns in REQUIRED_PATTERNS.items():
        path = Path(path_text)
        text = (ROOT / path).read_text(encoding="utf-8")
        for pattern in patterns:
            if not re.search(pattern, text, flags=re.IGNORECASE):
                findings.append(
                    DriftFinding(
                        rule_id="required_current_claim_missing",
                        path=path_text,
                        line=1,
                        message=f"Missing required current Tyler status claim matching /{pattern}/.",
                        excerpt="",
                    )
                )
    return findings


def build_doc_drift_report() -> dict[str, Any]:
    """Build the active Tyler doc-drift report."""

    paths = _iter_active_docs()
    findings = [*_find_forbidden_claims(paths), *_missing_required_claims()]
    return {
        "sources": [str(path) for path in paths],
        "summary": {
            "active_docs_scanned": len(paths),
            "findings": len(findings),
        },
        "findings": [asdict(item) for item in findings],
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render a compact maintainer-readable doc-drift report."""

    lines = [
        "# Tyler Doc Drift Report",
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
                "- `{path}:{line}` `{rule_id}`: {message}".format(
                    path=finding["path"],
                    line=finding["line"],
                    rule_id=finding["rule_id"],
                    message=finding["message"],
                )
            )
    else:
        lines.append("No active Tyler doc drift found.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """Run the active Tyler doc-drift checker."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args()

    report = build_doc_drift_report()
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report))
    if args.fail_on_findings and report["findings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
