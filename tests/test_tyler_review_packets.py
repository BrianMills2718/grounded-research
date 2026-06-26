"""Tests for Tyler requirement review packet generation."""

from __future__ import annotations

from pathlib import Path

from scripts.generate_tyler_review_packets import build_review_report, write_review_outputs


def test_review_report_accounts_for_every_tyler_requirement() -> None:
    """Review report should classify every structured Tyler row exactly once."""
    report = build_review_report()

    assert report["summary"]["requirements"] == 36
    assert len(report["requirements"]) == 36
    assert report["summary"]["deterministic_pass"] == 36
    assert report["summary"]["deterministic_needs_review"] == 0
    assert sum(report["by_robustness_status"].values()) == 36


def test_review_report_distinguishes_robust_from_judgment_rows() -> None:
    """Review statuses should not treat all passing rows as local unit-test closures."""
    report = build_review_report()

    assert report["summary"]["robust_local_or_prompt_closures"] == 21
    assert report["summary"]["accepted_non_code_reviews"] == 12
    assert report["summary"]["artifact_backed_reviews"] == 2
    assert report["summary"]["shared_infra_reviews"] == 1


def test_review_report_marks_judgment_rows_with_judgment_mode() -> None:
    """B/C/D rows should remain visible for human or LLM judgment."""
    report = build_review_report()

    judgment_rows = [
        row for row in report["requirements"] if row["evidence_grade"] in {"B", "C", "D"}
    ]

    assert len(judgment_rows) == 15
    assert all("llm_or_human_judgment" in row["review_modes"] for row in judgment_rows)


def test_write_review_outputs_creates_packet_per_requirement(tmp_path: Path) -> None:
    """Packet generation should produce one review packet per Tyler row."""
    output_dir = tmp_path / "tyler_requirement_reviews"

    report = write_review_outputs(output_dir)

    packets = sorted((output_dir / "packets").glob("*.md"))
    assert len(packets) == report["summary"]["requirements"]
    assert (output_dir / "deterministic_report.json").exists()
    assert (output_dir / "summary.md").exists()
    sample = (output_dir / "packets" / "S2-QUERY-MODEL-001.md").read_text(encoding="utf-8")
    assert "Tyler Requirement Review: S2-QUERY-MODEL-001" in sample
    assert "Review Rubric" in sample
