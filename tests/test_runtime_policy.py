"""Tests for run-level runtime reliability policy."""

from __future__ import annotations

from pathlib import Path

from grounded_research.runtime_policy import configure_run_runtime


def test_configure_run_runtime_sets_run_local_db_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Run runtime policy should derive a run-local observability DB path."""
    monkeypatch.setenv("LLM_CLIENT_DB_PATH", "")
    result = configure_run_runtime("run-123", tmp_path / "output")

    assert result["timeout_policy"] == "ban"
    assert result["db_path"] == str(tmp_path / "output" / "llm_observability.db")
