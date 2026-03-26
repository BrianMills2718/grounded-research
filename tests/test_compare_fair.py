"""Tests for fair-comparison harness runtime policy wiring."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts import compare_fair as compare_fair_module


@pytest.mark.asyncio
async def test_compare_fair_uses_pipeline_safe_runtime_policy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Fair comparison should set allow-mode timeouts and a local DB path."""
    report_a = tmp_path / "a.md"
    report_b = tmp_path / "b.md"
    report_a.write_text("# A")
    report_b.write_text("# B")

    monkeypatch.setattr(compare_fair_module, "PROJECT_ROOT", tmp_path)

    async def fake_acall_llm(model, messages, task, trace_id, max_budget):
        assert os.environ["LLM_CLIENT_TIMEOUT_POLICY"] == "allow"
        assert "/output/fair_" in os.environ["LLM_CLIENT_DB_PATH"]
        assert os.environ["LLM_CLIENT_DB_PATH"].endswith("_llm_observability.db")
        return type("Result", (), {"content": "judge output"})()

    monkeypatch.setattr("llm_client.acall_llm", fake_acall_llm)

    await compare_fair_module.compare_fair(report_a, report_b)

    assert list((tmp_path / "output").glob("fair_*.md"))
