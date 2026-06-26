"""Ensure Tyler docs keep provenance and current-status warnings."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
REQUIRED_MARKER = "Provenance/status: Tyler review/provenance artifact. Preserve for audit."
REQUIRED_CURRENT_STATUS_REFS = (
    "docs/MAINTAINER_START_HERE.md",
    "docs/tyler_requirements.yaml",
    "docs/tyler_requirements_registry.json",
)


@dataclass(frozen=True)
class ProvenanceFinding:
    """One Tyler document missing required provenance guidance."""

    path: Path
    finding: str

    def render(self) -> str:
        """Render the finding in grep-friendly form."""
        return f"{self.path}: {self.finding}"


def tyler_markdown_docs(docs_dir: Path = DOCS_DIR) -> list[Path]:
    """Return top-level Tyler Markdown artifacts that need provenance warnings."""
    return sorted(docs_dir.glob("TYLER*.md"))


def check_doc(path: Path) -> list[ProvenanceFinding]:
    """Check one Tyler Markdown artifact for provenance and status guidance."""
    text = path.read_text(encoding="utf-8")
    findings: list[ProvenanceFinding] = []
    if REQUIRED_MARKER not in text:
        findings.append(ProvenanceFinding(path, "missing_provenance_warning"))
    for required_ref in REQUIRED_CURRENT_STATUS_REFS:
        if required_ref not in text:
            findings.append(
                ProvenanceFinding(path, f"missing_current_status_ref:{required_ref}")
            )
    return findings


def build_report(docs_dir: Path = DOCS_DIR) -> dict[str, object]:
    """Build a machine-readable provenance-check report."""
    docs = tyler_markdown_docs(docs_dir)
    findings = [finding for path in docs for finding in check_doc(path)]
    return {
        "summary": {
            "docs": len(docs),
            "findings": len(findings),
        },
        "docs": [str(path.relative_to(ROOT)) for path in docs],
        "findings": [
            {
                "path": str(finding.path.relative_to(ROOT)),
                "finding": finding.finding,
            }
            for finding in findings
        ],
    }


def render_markdown(report: dict[str, object]) -> str:
    """Render the provenance-check report for maintainer review."""
    summary = report["summary"]
    assert isinstance(summary, dict)
    findings = report["findings"]
    assert isinstance(findings, list)
    lines = [
        "# Tyler Doc Provenance Check",
        "",
        f"- Docs checked: `{summary['docs']}`",
        f"- Findings: `{summary['findings']}`",
        "",
    ]
    if findings:
        lines.append("## Findings")
        lines.append("")
        for finding in findings:
            assert isinstance(finding, dict)
            lines.append(f"- `{finding['path']}`: `{finding['finding']}`")
    else:
        lines.append("No Tyler doc provenance gaps found.")
    return "\n".join(lines) + "\n"


def main() -> int:
    """Run the Tyler doc provenance checker."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args()

    report = build_report()
    if args.format == "json":
        import json

        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report), end="")

    summary = report["summary"]
    assert isinstance(summary, dict)
    if args.fail_on_findings and int(summary["findings"]) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
