"""Tests for export-layer runtime policy wiring."""

from __future__ import annotations

import pytest

from grounded_research.export import generate_report
from grounded_research.models import Claim, ClaimLedger, EvidenceBundle, EvidenceItem, PipelineState, ResearchQuestion, SourceRecord


@pytest.mark.asyncio
async def test_generate_report_passes_configured_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Structured synthesis should use the configured finite request timeout."""
    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, timeout):
        assert task == "report_synthesis"
        assert timeout == 240
        return response_model(
            title="Test Report",
            question="What is the evidence?",
            recommendation="Recommendation citing C-1.",
            cited_claim_ids=["C-1"],
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)

    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What is the evidence?"),
        evidence_bundle=EvidenceBundle(
            question=ResearchQuestion(text="What is the evidence?"),
            sources=[
                SourceRecord(
                    id="S-1",
                    url="https://example.com",
                    title="Source",
                    quality_tier="reliable",
                )
            ],
            evidence=[
                EvidenceItem(
                    id="E-1",
                    source_id="S-1",
                    content="Evidence content",
                    content_type="text",
                )
            ],
        ),
        claim_ledger=ClaimLedger(
            claims=[
                Claim(
                    id="C-1",
                    statement="A grounded claim.",
                    source_raw_claim_ids=["RC-1"],
                    analyst_sources=["Alpha"],
                    evidence_ids=["E-1"],
                    confidence="high",
                )
            ],
            disputes=[],
            arbitration_results=[],
        ),
    )

    report = await generate_report(state, trace_id="trace-1", max_budget=0.5)

    assert report.cited_claim_ids == ["C-1"]
