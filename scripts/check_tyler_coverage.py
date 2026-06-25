"""Report Tyler requirement coverage quality.

This is a non-strict read model over the current Tyler ledger. It makes weak
closure evidence visible as structured data before the project promotes the
ledger to a governed YAML/JSON source of truth.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_tyler_traceability import (  # noqa: E402
    LEDGER_PATH,
    ROOT,
    TYLER_SOURCE_ALIASES,
    TableRow,
    _code_spans,
    _extract_references,
    _parse_table,
)


@dataclass(frozen=True)
class CoverageEvidence:
    """One typed evidence reference for a Tyler requirement row."""

    kind: str
    target: str
    exists: bool
    symbol: str | None = None


@dataclass(frozen=True)
class CoverageRequirement:
    """One normalized Tyler requirement row with coverage-quality metadata."""

    requirement_id: str
    requirement_class: str
    closure_status: str
    evidence_grade: str
    anchor_status: str
    tyler_sources: list[str]
    owner: str
    severity: str
    evidence: list[CoverageEvidence]
    findings: list[str]
    adversarial_notes: list[str]


RUNTIME_ARTIFACT_PATTERN = re.compile(r"output/[A-Za-z0-9_./*\-]+")


def _source_aliases(text: str) -> list[str]:
    """Return Tyler source references mentioned in a row."""

    sources: list[str] = []
    for raw in _code_spans(text):
        alias = TYLER_SOURCE_ALIASES.get(raw)
        if alias is not None:
            sources.append(alias)
    return sorted(set(sources))


def _anchor_status(row: TableRow) -> str:
    """Classify whether the row has exact Tyler source anchoring."""

    source_text = row.fields.get("tyler_source", "")
    if not source_text.strip():
        return "missing"
    if re.search(r"(:L?\d+|#L\d+|\blines?\s+\d+)", source_text, flags=re.IGNORECASE):
        return "line_level"
    if _source_aliases(source_text):
        return "section_only"
    return "missing"


def _classify_requirement(row: TableRow, evidence: list[CoverageEvidence]) -> str:
    """Infer the current requirement class from ledger metadata."""

    spec_id = row.key
    classification = row.fields.get("classification", "")
    text = " ".join(row.fields.values()).lower()
    evidence_kinds = {item.kind for item in evidence}

    if classification == "tyler_ambiguity":
        return "ambiguity"
    if classification == "extension":
        return "extension"
    if classification == "stale_doc" or spec_id.startswith("DOC-"):
        return "doc_status"
    if row.fields.get("next_action") == "operational_watch_reopen_on_threshold":
        return "operational_watch"
    if spec_id.startswith("SC-") or "tyler_v1_models.py" in text:
        return "schema_contract"
    if "model" in text or "frontier" in text or "config" in evidence_kinds:
        return "model_config"
    if "prompt" in text or "prompt_template" in evidence_kinds:
        return "prompt_template"
    if "schema" in text:
        return "schema_contract"
    if (
        classification == "shared_infra_blocked"
        or "open_web_retrieval" in text
        or "tavily" in text
        or "exa" in text
    ):
        return "provider_behavior"
    if "trace.json" in text or "report.md" in text or "handoff.json" in text:
        return "output_artifact"
    return "runtime_behavior"


def _evidence_from_refs(row: TableRow) -> list[CoverageEvidence]:
    """Convert existing traceability references into coverage evidence refs."""

    items: list[CoverageEvidence] = []
    for ref in _extract_references(row):
        if ref.kind == "external_test":
            kind = "shared_infra_test"
        elif ref.kind == "external_source":
            kind = "shared_infra_source"
        elif ref.kind == "test":
            kind = "local_test"
        elif ref.path.startswith("prompts/"):
            kind = "prompt_template"
        elif ref.path.startswith("docs/"):
            kind = "doc"
        elif ref.path.startswith("config/"):
            kind = "config"
        elif ref.path.startswith("2026_0325_tyler_feedback/"):
            kind = "tyler_source"
        else:
            kind = "local_source"
        items.append(
            CoverageEvidence(
                kind=kind,
                target=ref.path,
                symbol=ref.symbol,
                exists=ref.exists,
            )
        )

    text = " ".join(row.fields.values())
    for raw in sorted(set(RUNTIME_ARTIFACT_PATTERN.findall(text))):
        path = raw.rstrip(".,;)")
        exists = (
            any((ROOT / "output").glob(path.removeprefix("output/")))
            if "*" in path
            else (ROOT / path).exists()
        )
        items.append(CoverageEvidence(kind="runtime_artifact", target=path, symbol=None, exists=exists))

    return sorted(items, key=lambda item: (item.kind, item.target, item.symbol or ""))


def _evidence_kinds(evidence: list[CoverageEvidence]) -> set[str]:
    """Return the set of evidence kinds present on a row."""

    return {item.kind for item in evidence}


def _grade_requirement(
    *,
    requirement_class: str,
    closure_status: str,
    evidence: list[CoverageEvidence],
) -> str:
    """Assign a conservative evidence grade from the current row evidence."""

    kinds = _evidence_kinds(evidence)
    has_local_test = "local_test" in kinds
    has_local_impl = bool({"local_source", "prompt_template", "config"} & kinds)
    has_runtime = "runtime_artifact" in kinds
    has_shared = bool({"shared_infra_source", "shared_infra_test"} & kinds)
    has_doc = "doc" in kinds or "tyler_source" in kinds

    if requirement_class in {"ambiguity", "extension", "doc_status"}:
        return "D" if has_doc else "F"
    if requirement_class == "operational_watch":
        return "B" if has_runtime else "F"
    if has_local_test and has_local_impl:
        return "A"
    if has_runtime and has_local_impl:
        return "B"
    if has_shared:
        return "C"
    if closure_status not in {"verified_fixed", "operational_watch_reopen_on_threshold"} and has_doc:
        return "D"
    return "F"


def _findings_for(
    *,
    row: TableRow,
    requirement_class: str,
    grade: str,
    anchor_status: str,
    evidence: list[CoverageEvidence],
) -> list[str]:
    """Build human-readable coverage findings for one row."""

    findings: list[str] = []
    kinds = _evidence_kinds(evidence)
    if anchor_status != "line_level":
        findings.append(f"source_anchor_{anchor_status}")
    if grade == "F":
        findings.append("insufficient_evidence_for_closure")
    if requirement_class == "runtime_behavior" and "local_test" not in kinds:
        findings.append("runtime_row_without_local_test")
    if requirement_class == "schema_contract" and "local_test" not in kinds:
        findings.append("schema_row_without_model_test")
    if requirement_class == "prompt_template" and "prompt_template" not in kinds:
        findings.append("prompt_row_without_prompt_template_ref")
    if requirement_class == "provider_behavior" and not (
        {"shared_infra_source", "shared_infra_test"} & kinds
    ):
        findings.append("provider_row_without_shared_infra_ref")
    if requirement_class in {"output_artifact", "operational_watch"} and "runtime_artifact" not in kinds:
        findings.append("runtime_artifact_row_without_artifact")
    if requirement_class == "doc_status" and "doc" not in kinds:
        findings.append("doc_status_row_without_doc_ref")
    if any(not item.exists for item in evidence):
        findings.append("evidence_ref_missing_locally")
    if row.fields.get("classification") == "shared_infra_blocked":
        owner = row.fields.get("owner", "")
        if not any(name in owner for name in ("llm_client", "open_web_retrieval", "prompt_eval")):
            findings.append("shared_infra_owner_not_explicit")
    return findings


def _adversarial_notes(requirement_class: str, grade: str, findings: list[str]) -> list[str]:
    """Suggest adversarial checks for future stricter audit passes."""

    notes: list[str] = []
    if grade in {"A", "B"}:
        notes.append("Verify the cited test or artifact asserts Tyler behavior, not only local shape.")
    if requirement_class in {"provider_behavior", "model_config"}:
        notes.append("Confirm shared-infra owner, command, and artifact before strict closure.")
    if "source_anchor_section_only" in findings:
        notes.append("Backfill exact Tyler line span before strong closure.")
    return notes


def evaluate_coverage_row(row: TableRow) -> CoverageRequirement:
    """Evaluate one Tyler ledger row against the audit quality standard."""

    evidence = _evidence_from_refs(row)
    requirement_class = _classify_requirement(row, evidence)
    closure_status = row.fields.get("next_action", "")
    anchor_status = _anchor_status(row)
    grade = _grade_requirement(
        requirement_class=requirement_class,
        closure_status=closure_status,
        evidence=evidence,
    )
    findings = _findings_for(
        row=row,
        requirement_class=requirement_class,
        grade=grade,
        anchor_status=anchor_status,
        evidence=evidence,
    )
    return CoverageRequirement(
        requirement_id=row.key,
        requirement_class=requirement_class,
        closure_status=closure_status,
        evidence_grade=grade,
        anchor_status=anchor_status,
        tyler_sources=_source_aliases(row.fields.get("tyler_source", "")),
        owner=row.fields.get("owner", ""),
        severity=row.fields.get("severity", ""),
        evidence=evidence,
        findings=findings,
        adversarial_notes=_adversarial_notes(requirement_class, grade, findings),
    )


def build_coverage_report() -> dict[str, Any]:
    """Build a Tyler requirement coverage report."""

    ledger_rows = _parse_table(LEDGER_PATH, "spec_id")
    requirements = [evaluate_coverage_row(row) for row in ledger_rows]

    by_grade: dict[str, int] = {}
    by_class: dict[str, int] = {}
    by_anchor: dict[str, int] = {}
    for requirement in requirements:
        by_grade[requirement.evidence_grade] = by_grade.get(requirement.evidence_grade, 0) + 1
        by_class[requirement.requirement_class] = (
            by_class.get(requirement.requirement_class, 0) + 1
        )
        by_anchor[requirement.anchor_status] = by_anchor.get(requirement.anchor_status, 0) + 1

    review_needed = [
        item.requirement_id
        for item in requirements
        if item.evidence_grade == "F" or item.anchor_status != "line_level"
    ]
    return {
        "sources": [str(LEDGER_PATH), "docs/TYLER_AUDIT_QUALITY_STANDARD.md"],
        "summary": {
            "requirements": len(requirements),
            "review_needed": len(review_needed),
            "line_anchor_pending": sum(
                1 for item in requirements if item.anchor_status != "line_level"
            ),
            "grade_f": by_grade.get("F", 0),
        },
        "by_grade": dict(sorted(by_grade.items())),
        "by_requirement_class": dict(sorted(by_class.items())),
        "by_anchor_status": dict(sorted(by_anchor.items())),
        "review_needed": review_needed,
        "requirements": [asdict(item) for item in requirements],
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render a human-readable Tyler coverage dashboard."""

    lines = [
        "# Tyler Coverage Report",
        "",
        "> Generated from the current ledger and audit quality standard.",
        "> This is a non-strict read model; grade and anchor gaps are not yet `make check` failures.",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ]
    for key, value in report["summary"].items():
        lines.append(f"| {key} | {value} |")

    for title, key_name, label in [
        ("Evidence Grades", "by_grade", "grade"),
        ("Requirement Classes", "by_requirement_class", "class"),
        ("Anchor Status", "by_anchor_status", "anchor_status"),
    ]:
        lines.extend(["", f"## {title}", "", f"| {label} | rows |", "|---|---:|"])
        for key, value in report[key_name].items():
            lines.append(f"| `{key}` | {value} |")

    lines.extend(["", "## Rows Needing Review", ""])
    if report["review_needed"]:
        for requirement_id in report["review_needed"]:
            lines.append(f"- `{requirement_id}`")
    else:
        lines.append("None.")

    lines.extend(["", "## Requirement Detail", ""])
    lines.append("| requirement | class | grade | anchor | findings |")
    lines.append("|---|---|---|---|---|")
    for requirement in report["requirements"]:
        findings = ", ".join(requirement["findings"]) if requirement["findings"] else "none"
        lines.append(
            "| `{requirement_id}` | `{requirement_class}` | `{evidence_grade}` | "
            "`{anchor_status}` | {findings} |".format(
                requirement_id=requirement["requirement_id"],
                requirement_class=requirement["requirement_class"],
                evidence_grade=requirement["evidence_grade"],
                anchor_status=requirement["anchor_status"],
                findings=findings,
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """Run the Tyler coverage CLI."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument(
        "--fail-on-grade-f",
        action="store_true",
        help="Exit non-zero if any row has grade F. Not used by make check yet.",
    )
    args = parser.parse_args()

    report = build_coverage_report()
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown(report))

    if args.fail_on_grade_f and report["summary"]["grade_f"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
