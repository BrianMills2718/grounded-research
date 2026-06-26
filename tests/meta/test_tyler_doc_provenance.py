"""Tests for Tyler document provenance warnings."""

from __future__ import annotations

from scripts.check_tyler_doc_provenance import (
    REQUIRED_MARKER,
    build_report,
    check_doc,
    render_markdown,
)


def test_tyler_doc_provenance_report_has_no_findings() -> None:
    """All top-level Tyler Markdown artifacts should carry provenance warnings."""
    report = build_report()

    assert report["summary"]["findings"] == 0
    assert report["findings"] == []


def test_tyler_doc_provenance_markdown_reports_clean_state() -> None:
    """The Markdown report should be useful when no gaps exist."""
    markdown = render_markdown(build_report())

    assert "# Tyler Doc Provenance Check" in markdown
    assert "No Tyler doc provenance gaps found." in markdown


def test_tyler_doc_provenance_negative_control(tmp_path) -> None:
    """A Tyler doc without the warning should fail the provenance check."""
    doc = tmp_path / "TYLER_EXAMPLE.md"
    doc.write_text("# Tyler Example\n\nHistorical claims.\n", encoding="utf-8")

    findings = check_doc(doc)

    assert REQUIRED_MARKER not in doc.read_text(encoding="utf-8")
    assert {finding.finding for finding in findings} >= {"missing_provenance_warning"}
