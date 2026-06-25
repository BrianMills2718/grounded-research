"""Tests for Tyler requirements coverage reporting."""

from __future__ import annotations

from scripts.check_tyler_coverage import (
    CoverageEvidence,
    _grade_requirement,
    build_coverage_report,
    evaluate_coverage_row,
    render_markdown,
)
from scripts.check_tyler_traceability import TableRow


def _negative_row(
    requirement_id: str,
    *,
    tyler_source: str = "`1. V1_Build_Plan_Step_By_Step.md` Stage 1",
    requirement: str = "Runtime behavior must be verified.",
    local_surface: str = "",
    evidence: str = "",
    classification: str = "local_divergence",
    owner: str = "grounded-research",
    next_action: str = "verified_fixed",
) -> TableRow:
    """Build one intentionally bad ledger row for negative-control tests."""
    return TableRow(
        source="negative-control",
        key=requirement_id,
        fields={
            "spec_id": requirement_id,
            "tyler_source": tyler_source,
            "tyler_requirement": requirement,
            "local_surface": local_surface,
            "evidence": evidence,
            "classification": classification,
            "severity": "high",
            "owner": owner,
            "next_action": next_action,
        },
    )


def test_tyler_coverage_report_builds_from_current_ledger() -> None:
    """Coverage report should expose every current Tyler ledger row."""
    report = build_coverage_report()

    assert report["summary"]["requirements"] == 36
    assert sum(report["by_grade"].values()) == 36
    assert sum(report["by_requirement_class"].values()) == 36
    assert len(report["requirements"]) == 36


def test_tyler_coverage_report_surfaces_anchor_backlog() -> None:
    """Current rows should be honest about missing line-level Tyler anchors."""
    report = build_coverage_report()

    assert report["summary"]["line_anchor_pending"] > 0
    assert "section_only" in report["by_anchor_status"]
    assert "S1-VALIDATION-001" in report["review_needed"]


def test_tyler_coverage_report_keeps_known_shared_infra_rows_visible() -> None:
    """Shared-infra-backed rows should remain inspectable in the registry."""
    report = build_coverage_report()
    rows = {row["requirement_id"]: row for row in report["requirements"]}

    assert rows["S2-TAVILY-DEPTH-001"]["evidence_grade"] in {"C", "F"}
    assert rows["S3-MODEL-VERSION-001"]["requirement_class"] == "model_config"
    assert rows["STATUS-FRONTIER-RUNTIME-001"]["requirement_class"] == "operational_watch"


def test_tyler_coverage_markdown_renders_review_sections() -> None:
    """Markdown output should be useful to maintainers."""
    markdown = render_markdown(build_coverage_report())

    assert "# Tyler Coverage Report" in markdown
    assert "## Evidence Grades" in markdown
    assert "## Rows Needing Review" in markdown
    assert "`S1-VALIDATION-001`" in markdown


def test_grade_requirement_rejects_runtime_doc_only_closure() -> None:
    """Runtime behavior cannot close with doc-only evidence."""
    grade = _grade_requirement(
        requirement_class="runtime_behavior",
        closure_status="verified_fixed",
        evidence=[CoverageEvidence(kind="doc", target="docs/example.md", exists=True)],
    )

    assert grade == "F"


def test_grade_requirement_accepts_local_tested_runtime_closure() -> None:
    """Runtime behavior with local implementation and test evidence is strong."""
    grade = _grade_requirement(
        requirement_class="runtime_behavior",
        closure_status="verified_fixed",
        evidence=[
            CoverageEvidence(kind="local_source", target="src/example.py", exists=True),
            CoverageEvidence(kind="local_test", target="tests/test_example.py", exists=True),
        ],
    )

    assert grade == "A"


def test_negative_control_closed_runtime_row_with_doc_only_evidence_fails() -> None:
    """A runtime row cannot close with documentation evidence only."""
    row = _negative_row(
        "NEG-RUNTIME-001",
        local_surface="`docs/TYLER_TRACEABILITY.md`",
        evidence="Document says this is fixed.",
    )

    result = evaluate_coverage_row(row)

    assert result.evidence_grade == "F"
    assert "runtime_row_without_local_test" in result.findings


def test_negative_control_schema_row_without_model_test_fails() -> None:
    """A schema row needs model/test evidence, not only model source."""
    row = _negative_row(
        "SC-NEG-001",
        requirement="Schema contract must be enforced.",
        local_surface="`src/grounded_research/tyler_v1_models.py`",
        evidence="Model exists but no test is cited.",
    )

    result = evaluate_coverage_row(row)

    assert result.evidence_grade == "F"
    assert result.requirement_class == "schema_contract"
    assert "schema_row_without_model_test" in result.findings


def test_negative_control_prompt_row_with_broken_render_ref_fails() -> None:
    """A prompt row with a missing prompt template ref should fail loudly."""
    row = _negative_row(
        "NEG-PROMPT-001",
        requirement="Prompt template must render.",
        local_surface="`prompts/does_not_exist.yaml`",
        evidence="Missing prompt path is intentionally cited.",
    )

    result = evaluate_coverage_row(row)

    assert result.evidence_grade == "F"
    assert result.requirement_class == "prompt_template"
    assert "evidence_ref_missing_locally" in result.findings


def test_negative_control_shared_infra_row_without_owner_fails() -> None:
    """A shared-infra row must name the owner repo explicitly."""
    row = _negative_row(
        "NEG-SHARED-001",
        requirement="Provider behavior must be verified in shared infra.",
        local_surface="`src/grounded_research/tools/web_search.py`",
        evidence="Provider behavior is claimed fixed.",
        classification="shared_infra_blocked",
        owner="shared runtime",
    )

    result = evaluate_coverage_row(row)

    assert "shared_infra_owner_not_explicit" in result.findings


def test_negative_control_runtime_artifact_row_without_artifact_fails() -> None:
    """Output/runtime-artifact rows need a concrete artifact ref."""
    row = _negative_row(
        "NEG-OUTPUT-001",
        requirement="Final report artifact must prove the behavior.",
        local_surface="`src/grounded_research/export.py`",
        evidence="report.md is mentioned but no output path is cited.",
    )

    result = evaluate_coverage_row(row)

    assert result.requirement_class == "output_artifact"
    assert "runtime_artifact_row_without_artifact" in result.findings


def test_negative_control_row_without_line_anchor_is_flagged() -> None:
    """A Tyler source section without line span should remain review-needed."""
    row = _negative_row("NEG-ANCHOR-001")

    result = evaluate_coverage_row(row)

    assert result.anchor_status == "section_only"
    assert "source_anchor_section_only" in result.findings


def test_negative_control_stale_doc_without_doc_ref_fails() -> None:
    """A stale-doc closure row should cite the document it closes."""
    row = _negative_row(
        "DOC-NEG-001",
        requirement="Status doc must not overclaim closure.",
        local_surface="",
        evidence="Fixed by prose with no doc ref.",
        classification="stale_doc",
    )

    result = evaluate_coverage_row(row)

    assert result.evidence_grade == "F"
    assert result.requirement_class == "doc_status"
    assert "doc_status_row_without_doc_ref" in result.findings
