"""Analyst-stage tests for coverage-target wiring and retry behavior."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from grounded_research.analysts import run_analyst
from grounded_research.models import AnalystRun, EvidenceBundle, EvidenceItem, ResearchQuestion, SourceRecord


def _make_bundle(evidence_count: int) -> EvidenceBundle:
    """Create a minimal evidence bundle for analyst-stage tests."""
    sources = [
        SourceRecord(
            id="S-1",
            url="https://example.com/source-1",
            title="Example source 1",
            quality_tier="authoritative",
        ),
        SourceRecord(
            id="S-2",
            url="https://example.com/source-2",
            title="Example source 2",
            quality_tier="reliable",
        ),
    ]
    evidence = [
        EvidenceItem(
            id=f"E-{i:08d}",
            source_id="S-1" if i % 2 == 0 else "S-2",
            content=f"Evidence item {i} mentions program {i}.",
            content_type="text",
        )
        for i in range(1, evidence_count + 1)
    ]
    return EvidenceBundle(
        question=ResearchQuestion(text="What does the evidence say?"),
        sources=sources,
        evidence=evidence,
        gaps=[],
    )


def _make_result(label: str, claim_count: int) -> AnalystRun:
    """Create a minimal successful AnalystRun with the requested claim count."""
    claims = [
        {
            "id": f"RC-{i:08d}",
            "statement": f"Claim {i}",
            "evidence_ids": ["E-00000001"],
            "confidence": "medium",
        }
        for i in range(1, claim_count + 1)
    ]
    return AnalystRun(
        analyst_label=label,
        frame="verification_first",
        model="test-model",
        claims=claims,
        recommendations=[
            {
                "statement": "Recommendation",
                "supporting_claim_ids": [claim["id"] for claim in claims[:3]],
                "conditions": "Default recommendation conditions.",
            }
        ],
        counterarguments=[{"target": "recommendation", "argument": "Counterargument", "evidence_ids": ["E-00000001"]}],
        summary="Summary",
        completed_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_run_analyst_retries_when_rich_bundle_is_under_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rich bundles should trigger one retry when claim count is materially low."""
    bundle = _make_bundle(evidence_count=40)
    calls: list[dict[str, object]] = []
    results = [_make_result("Alpha", 4), _make_result("Alpha", 8)]

    async def fake_call(*args, **kwargs):
        calls.append({"trace_id": kwargs["trace_id"], "messages": args[1]})
        return results[len(calls) - 1], {"provider": "test"}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_call)
    monkeypatch.setattr(
        "grounded_research.analysts.get_depth_config",
        lambda: {"analyst_claim_target": 8},
    )
    monkeypatch.setattr(
        "grounded_research.analysts.get_analysis_coverage_config",
        lambda: {
            "analyst_retry_on_undercoverage": True,
            "analyst_retry_min_evidence_items": 25,
            "analyst_retry_min_claim_ratio": 0.75,
            "analyst_retry_max_attempts": 1,
        },
    )

    result = await run_analyst(
        model="test-model",
        label="Alpha",
        bundle=bundle,
        frame="verification_first",
        trace_id="trace",
        max_budget=1.0,
    )

    assert len(calls) == 2
    assert calls[0]["trace_id"] == "trace/Alpha"
    assert calls[1]["trace_id"] == "trace/Alpha/coverage_retry_1"
    assert "approximately 8 distinct evidence-backed claims" in calls[0]["messages"][1]["content"]
    assert "Coverage correction:" in calls[1]["messages"][1]["content"]
    assert len(result.claims) == 8


@pytest.mark.asyncio
async def test_run_analyst_skips_retry_for_sparse_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sparse bundles should not retry just because claim count is low."""
    bundle = _make_bundle(evidence_count=10)
    calls: list[dict[str, object]] = []

    async def fake_call(*args, **kwargs):
        calls.append({"trace_id": kwargs["trace_id"]})
        return _make_result("Alpha", 4), {"provider": "test"}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_call)
    monkeypatch.setattr(
        "grounded_research.analysts.get_depth_config",
        lambda: {"analyst_claim_target": 8},
    )
    monkeypatch.setattr(
        "grounded_research.analysts.get_analysis_coverage_config",
        lambda: {
            "analyst_retry_on_undercoverage": True,
            "analyst_retry_min_evidence_items": 25,
            "analyst_retry_min_claim_ratio": 0.75,
            "analyst_retry_max_attempts": 1,
        },
    )

    result = await run_analyst(
        model="test-model",
        label="Alpha",
        bundle=bundle,
        frame="verification_first",
        trace_id="trace",
        max_budget=1.0,
    )

    assert len(calls) == 1
    assert calls[0]["trace_id"] == "trace/Alpha"
    assert len(result.claims) == 4


@pytest.mark.asyncio
async def test_run_analyst_uses_retry_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """The retry result should replace the initial under-covered output."""
    bundle = _make_bundle(evidence_count=30)
    results = [_make_result("Alpha", 3), _make_result("Alpha", 7)]

    async def fake_call(*args, **kwargs):
        return results.pop(0), {"provider": "test"}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_call)
    monkeypatch.setattr(
        "grounded_research.analysts.get_depth_config",
        lambda: {"analyst_claim_target": 8},
    )
    monkeypatch.setattr(
        "grounded_research.analysts.get_analysis_coverage_config",
        lambda: {
            "analyst_retry_on_undercoverage": True,
            "analyst_retry_min_evidence_items": 25,
            "analyst_retry_min_claim_ratio": 0.75,
            "analyst_retry_max_attempts": 1,
        },
    )

    result = await run_analyst(
        model="test-model",
        label="Alpha",
        bundle=bundle,
        frame="verification_first",
        trace_id="trace",
        max_budget=1.0,
    )

    assert len(result.claims) == 7
