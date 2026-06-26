"""Tests for active Tyler doc-drift detection."""

from __future__ import annotations

from scripts.check_tyler_doc_drift import (
    DriftRule,
    _find_forbidden_claims,
    build_doc_drift_report,
    render_markdown,
)
from scripts.check_tyler_doc_drift import ROOT as DOC_DRIFT_ROOT


def test_tyler_doc_drift_report_has_no_current_findings() -> None:
    """Active maintainer docs should not contradict the current Tyler ledger."""
    report = build_doc_drift_report()

    assert report["summary"]["findings"] == 0
    assert report["findings"] == []


def test_tyler_doc_drift_markdown_reports_clean_state() -> None:
    """The Markdown report should be useful when no drift exists."""
    markdown = render_markdown(build_doc_drift_report())

    assert "# Tyler Doc Drift Report" in markdown
    assert "No active Tyler doc drift found." in markdown


def test_tyler_doc_drift_negative_control_catches_stale_claim(
    tmp_path, monkeypatch
) -> None:
    """The checker should catch the exact stale claim family it guards."""
    doc = tmp_path / "README.md"
    doc.write_text(
        "The remaining exact gap is the Gemini 3.1 Pro model-version substitution.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("scripts.check_tyler_doc_drift.ROOT", tmp_path)
    monkeypatch.setattr(
        "scripts.check_tyler_doc_drift.FORBIDDEN_RULES",
        (
            DriftRule(
                rule_id="gemini_exact_gap_open",
                pattern=r"remaining exact(?:-model)? gap.*Gemini",
                message="Exact Gemini parity is closed.",
            ),
        ),
    )

    findings = _find_forbidden_claims([doc.relative_to(tmp_path)])

    assert len(findings) == 1
    assert findings[0].rule_id == "gemini_exact_gap_open"


def test_doc_drift_root_points_at_repo() -> None:
    """The script should resolve paths from the repository root."""
    assert (DOC_DRIFT_ROOT / "docs/TYLER_SPEC_GAP_LEDGER.md").exists()
