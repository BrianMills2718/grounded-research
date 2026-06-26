"""Tests for raw Tyler source manifest verification."""

from __future__ import annotations

from scripts.check_tyler_source_manifest import (
    EXPECTED_SOURCES,
    _line_count,
    build_source_manifest_report,
    render_markdown,
)
from scripts.check_tyler_source_manifest import ROOT as SOURCE_ROOT


def test_tyler_source_manifest_matches_tracked_files() -> None:
    """The tracked raw Tyler packet should match the manifest."""
    report = build_source_manifest_report()

    assert report["summary"]["files"] == 4
    assert report["summary"]["total_expected_lines"] == 2377
    assert report["summary"]["failures"] == 0
    assert all(row["exists"] and row["ok"] for row in report["files"])


def test_tyler_source_manifest_markdown_renders_file_table() -> None:
    """The Markdown report should be useful to maintainers."""
    markdown = render_markdown(build_source_manifest_report())

    assert "# Tyler Source Manifest Check" in markdown
    assert "1. V1_Build_Plan_Step_By_Step.md" in markdown


def test_tyler_source_manifest_line_counts_are_exact() -> None:
    """Expected line counts should match the raw source files."""
    observed = {
        expected.path: _line_count(SOURCE_ROOT / expected.path)
        for expected in EXPECTED_SOURCES
    }

    assert observed["2026_0325_tyler_feedback/4. V1_PROMPTS.md"] == 1163
