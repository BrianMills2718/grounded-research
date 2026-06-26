"""Tests for current-code Tyler evidence auditing."""

from __future__ import annotations

from scripts.check_tyler_code_audit import (
    _audit_requirement,
    build_code_audit_report,
    render_markdown,
)


def _row(*, kinds: list[str], requirement_class: str = "runtime_behavior") -> dict:
    """Build a minimal coverage row for code-audit negative controls."""

    return {
        "requirement_id": "NEG-001",
        "requirement_class": requirement_class,
        "evidence": [{"kind": kind} for kind in kinds],
    }


def test_tyler_code_audit_report_has_no_current_findings() -> None:
    """Current non-doc Tyler rows should cite code/config and verification evidence."""
    report = build_code_audit_report()

    assert report["summary"]["current_code_audited"] == 24
    assert report["summary"]["findings"] == 0
    assert report["findings"] == []


def test_tyler_code_audit_markdown_reports_clean_state() -> None:
    """The Markdown report should be useful when no gaps exist."""
    markdown = render_markdown(build_code_audit_report())

    assert "# Tyler Current-Code Audit" in markdown
    assert "No current-code evidence gaps found." in markdown


def test_code_audit_negative_control_rejects_doc_only_runtime_row() -> None:
    """A runtime row with only doc evidence should fail the current-code audit."""
    findings = _audit_requirement(_row(kinds=["doc"]))

    assert {finding.finding for finding in findings} == {
        "missing_current_implementation_evidence",
        "missing_current_verification_evidence",
    }


def test_code_audit_accepts_shared_runtime_evidence() -> None:
    """Shared test plus runtime artifact evidence can close non-local rows."""
    findings = _audit_requirement(
        _row(kinds=["shared_infra_test", "runtime_artifact"], requirement_class="model_config")
    )

    assert findings == []


def test_code_audit_skips_doc_status_rows() -> None:
    """Doc-governance rows are handled by coverage/doc-drift checks."""
    assert _audit_requirement(_row(kinds=["doc"], requirement_class="doc_status")) == []
