"""Generate identify-only Tyler requirement review packets and summary.

The review layer classifies every structured Tyler requirement by current proof
mode. It does not remediate gaps; it makes local-test, artifact, shared-infra,
doc, ambiguity, extension, and watch evidence explicit for later review.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_tyler_traceability import LEDGER_PATH, _parse_table  # noqa: E402
from scripts.sync_tyler_requirements_yaml import YAML_PATH, load_yaml, validate_model  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("output/tyler_requirement_reviews")
RUBRIC_PATH = Path("docs/TYLER_REQUIREMENT_REVIEW_RUBRIC.md")


@dataclass(frozen=True)
class ReviewRecord:
    """One deterministic review result for a Tyler requirement."""

    requirement_id: str
    requirement_class: str
    evidence_grade: str
    deterministic_status: str
    robustness_status: str
    review_modes: list[str]
    findings: list[str]
    recommended_next_action: str


def _ledger_by_id() -> dict[str, dict[str, str]]:
    """Return ledger fields keyed by requirement ID."""

    return {row.key: row.fields for row in _parse_table(LEDGER_PATH, "spec_id")}


def _evidence_kinds(requirement: dict[str, Any]) -> set[str]:
    """Return evidence kind set for one YAML requirement row."""

    return set(requirement.get("evidence_kinds", []))


def _classify_review(requirement: dict[str, Any]) -> ReviewRecord:
    """Classify one requirement's current review status."""

    requirement_id = requirement["id"]
    requirement_class = requirement["requirement_class"]
    evidence_grade = requirement["evidence_grade"]
    kinds = _evidence_kinds(requirement)
    findings = list(requirement.get("findings", []))
    review_modes = ["metadata_policy_check"]

    if "local_test" in kinds:
        review_modes.append("unit_or_integration_test")
    if "prompt_template" in kinds:
        review_modes.append("prompt_render_test")
    if "runtime_artifact" in kinds:
        review_modes.append("runtime_artifact_check")
    if kinds & {"shared_infra_source", "shared_infra_test"}:
        review_modes.append("shared_infra_evidence")
    if "doc" in kinds:
        review_modes.append("doc_drift_check")

    if requirement_class == "doc_status":
        robustness_status = "accepted_doc_status"
        recommended_next_action = "Keep doc-drift gate active; no runtime unit test expected."
    elif requirement_class == "ambiguity":
        robustness_status = "accepted_ambiguity"
        review_modes.append("ambiguity_review")
        recommended_next_action = "Review Tyler ambiguity rationale; no silent runtime assumption expected."
    elif requirement_class == "extension":
        robustness_status = "accepted_extension"
        review_modes.append("extension_review")
        recommended_next_action = "Review non-conflict rationale and owner before strengthening closure."
    elif requirement_class == "operational_watch":
        robustness_status = "operational_watch"
        review_modes.append("operational_watch_review")
        recommended_next_action = "Review artifact freshness, threshold, and reopen rule."
    elif evidence_grade == "A" and {"local_source", "local_test"} <= kinds:
        robustness_status = (
            "prompt_template_closure" if requirement_class == "prompt_template" else "robust_local_closure"
        )
        recommended_next_action = "Spot-check that cited tests assert Tyler-specific behavior."
    elif "runtime_artifact" in kinds:
        robustness_status = "artifact_backed_review"
        review_modes.append("llm_or_human_judgment")
        recommended_next_action = "Inspect artifact command, freshness, and reproducibility."
    elif kinds & {"shared_infra_source", "shared_infra_test"}:
        robustness_status = "shared_infra_review"
        review_modes.append("llm_or_human_judgment")
        recommended_next_action = "Confirm shared-infra owner, test, and current upstream state."
    else:
        robustness_status = "needs_review"
        review_modes.append("llm_or_human_judgment")
        recommended_next_action = "Review row manually; deterministic evidence is not strong enough."

    if evidence_grade in {"B", "C", "D"} and "llm_or_human_judgment" not in review_modes:
        review_modes.append("llm_or_human_judgment")
    if evidence_grade == "F":
        findings.append("grade_f_insufficient_closure")
    if any(not item.get("exists", False) for item in requirement.get("evidence", [])):
        findings.append("missing_evidence_reference")

    deterministic_status = "pass" if not findings else "needs_review"
    return ReviewRecord(
        requirement_id=requirement_id,
        requirement_class=requirement_class,
        evidence_grade=evidence_grade,
        deterministic_status=deterministic_status,
        robustness_status=robustness_status if not findings else "needs_review",
        review_modes=sorted(set(review_modes)),
        findings=sorted(set(findings)),
        recommended_next_action=recommended_next_action,
    )


def build_review_report() -> dict[str, Any]:
    """Build the deterministic review report for every Tyler requirement."""

    model = load_yaml()
    policy_findings = validate_model(model)
    records = [_classify_review(row) for row in model["requirements"]]
    by_status = Counter(record.robustness_status for record in records)
    by_mode = Counter(mode for record in records for mode in record.review_modes)
    by_grade = Counter(record.evidence_grade for record in records)
    return {
        "sources": [str(YAML_PATH), str(RUBRIC_PATH), str(LEDGER_PATH)],
        "summary": {
            "requirements": len(records),
            "deterministic_pass": sum(1 for record in records if record.deterministic_status == "pass"),
            "deterministic_needs_review": sum(
                1 for record in records if record.deterministic_status != "pass"
            ),
            "policy_findings": len(policy_findings),
            "robust_local_or_prompt_closures": by_status["robust_local_closure"]
            + by_status["prompt_template_closure"],
            "artifact_backed_reviews": by_status["artifact_backed_review"]
            + by_status["operational_watch"],
            "shared_infra_reviews": by_status["shared_infra_review"],
            "accepted_non_code_reviews": by_status["accepted_doc_status"]
            + by_status["accepted_ambiguity"]
            + by_status["accepted_extension"],
        },
        "by_robustness_status": dict(sorted(by_status.items())),
        "by_review_mode": dict(sorted(by_mode.items())),
        "by_grade": dict(sorted(by_grade.items())),
        "policy_findings": policy_findings,
        "requirements": [asdict(record) for record in records],
    }


def _packet_text(requirement: dict[str, Any], ledger_fields: dict[str, str], record: ReviewRecord) -> str:
    """Render one requirement review packet."""

    lines = [
        f"# Tyler Requirement Review: {requirement['id']}",
        "",
        "## Status",
        "",
        f"- Requirement class: `{requirement['requirement_class']}`",
        f"- Closure status: `{requirement['closure_status']}`",
        f"- Evidence grade: `{requirement['evidence_grade']}`",
        f"- Deterministic status: `{record.deterministic_status}`",
        f"- Robustness status: `{record.robustness_status}`",
        f"- Review modes: {', '.join(f'`{mode}`' for mode in record.review_modes)}",
        f"- Recommended next action: {record.recommended_next_action}",
        "",
        "## Tyler Requirement",
        "",
        ledger_fields.get("tyler_requirement", "(not found in ledger)"),
        "",
        "## Tyler Source",
        "",
        ledger_fields.get("tyler_source", "(not found in ledger)"),
        "",
        "## Local Surface",
        "",
        ledger_fields.get("local_surface", "(not found in ledger)"),
        "",
        "## Evidence Summary",
        "",
        ledger_fields.get("evidence", "(not found in ledger)"),
        "",
        "## Structured Evidence",
        "",
    ]
    for item in requirement.get("evidence", []):
        symbol = f"::{item['symbol']}" if item.get("symbol") else ""
        exists = "exists" if item.get("exists") else "missing"
        lines.append(f"- `{item['kind']}` `{item['target']}{symbol}` ({exists})")
    lines.extend(
        [
            "",
            "## Findings",
            "",
        ]
    )
    if record.findings:
        lines.extend(f"- `{finding}`" for finding in record.findings)
    else:
        lines.append("No deterministic findings.")
    lines.extend(
        [
            "",
            "## Adversarial Notes",
            "",
        ]
    )
    notes = requirement.get("adversarial_notes", [])
    if notes:
        lines.extend(f"- {note}" for note in notes)
    else:
        lines.append("No row-specific adversarial notes recorded.")
    lines.extend(
        [
            "",
            "## Review Rubric",
            "",
            "Use `docs/TYLER_REQUIREMENT_REVIEW_RUBRIC.md` to judge source fidelity, "
            "evidence relevance, evidence freshness, closure class fit, test strength, "
            "and residual risk.",
            "",
        ]
    )
    return "\n".join(lines)


def write_review_outputs(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Write review packets plus deterministic JSON/Markdown reports."""

    model = load_yaml()
    ledger = _ledger_by_id()
    report = build_review_report()
    records = {row["requirement_id"]: ReviewRecord(**row) for row in report["requirements"]}

    full_output_dir = REPO_ROOT / output_dir
    packets_dir = full_output_dir / "packets"
    packets_dir.mkdir(parents=True, exist_ok=True)
    for requirement in model["requirements"]:
        requirement_id = requirement["id"]
        packet = _packet_text(requirement, ledger.get(requirement_id, {}), records[requirement_id])
        (packets_dir / f"{requirement_id}.md").write_text(packet, encoding="utf-8")

    (full_output_dir / "deterministic_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (full_output_dir / "summary.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def render_markdown(report: dict[str, Any]) -> str:
    """Render deterministic review summary."""

    lines = [
        "# Tyler Requirement Review Summary",
        "",
        "This is an identify-only report. It classifies current evidence strength and review mode; it does not remediate findings.",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ]
    for key, value in report["summary"].items():
        lines.append(f"| {key} | {value} |")

    for title, key_name in [
        ("Robustness Status", "by_robustness_status"),
        ("Review Modes", "by_review_mode"),
        ("Evidence Grades", "by_grade"),
    ]:
        lines.extend(["", f"## {title}", "", "| value | rows |", "|---|---:|"])
        for key, value in report[key_name].items():
            lines.append(f"| `{key}` | {value} |")

    lines.extend(
        [
            "",
            "## Requirement Detail",
            "",
            "| requirement | class | grade | deterministic | robustness | review modes | findings |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["requirements"]:
        findings = ", ".join(f"`{finding}`" for finding in row["findings"]) or "none"
        modes = ", ".join(f"`{mode}`" for mode in row["review_modes"])
        display_row = {**row, "modes": modes, "findings_display": findings}
        lines.append(
            "| `{requirement_id}` | `{requirement_class}` | `{evidence_grade}` | "
            "`{deterministic_status}` | `{robustness_status}` | {modes} | {findings_display} |".format(
                **display_row
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """Run the Tyler requirement review packet generator."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--write", action="store_true", help="Write review packets and reports")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()

    report = write_review_outputs(args.output_dir) if args.write else build_review_report()
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
