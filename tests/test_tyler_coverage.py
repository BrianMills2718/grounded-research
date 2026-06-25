"""Tests for Tyler requirements coverage reporting."""

from __future__ import annotations

from scripts.check_tyler_coverage import (
    CoverageEvidence,
    _grade_requirement,
    build_coverage_report,
    render_markdown,
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
