"""Tests for Tyler-native Stage 2 runtime migration."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from grounded_research.collect import build_tyler_evidence_package, generate_search_queries_tyler_v1
from grounded_research.models import EvidenceBundle, EvidenceItem, ResearchQuestion, SourceRecord
from grounded_research.tyler_v1_models import DecompositionResult, ResearchPlan, StageSummary, SubQuestion


def _stage_summary(stage_name: str) -> StageSummary:
    return StageSummary(
        stage_name=stage_name,
        goal="goal",
        key_findings=["k1", "k2", "k3"],
        decisions_made=["d1"],
        outcome="outcome",
        reasoning="reasoning",
    )


def _tyler_decomposition() -> DecompositionResult:
    return DecompositionResult(
        core_question="What is the current evidence?",
        sub_questions=[
            SubQuestion(
                id="Q-1",
                question="What did pilot A show?",
                type="empirical",
                research_priority="high",
                search_guidance="official reports and evaluations",
            ),
            SubQuestion(
                id="Q-2",
                question="How should we interpret mixed findings?",
                type="interpretive",
                research_priority="medium",
                search_guidance="reviews and critiques",
            ),
        ],
        optimization_axes=["employment vs broader welfare"],
        research_plan=ResearchPlan(
            what_to_verify=["employment effect"],
            critical_source_types=["official docs", "academic"],
            falsification_targets=["contradictory RCT result", "N/A"],
        ),
        stage_summary=_stage_summary("Stage 1: Intake & Decomposition"),
    )


@pytest.mark.asyncio
async def test_generate_search_queries_tyler_v1_returns_mapped_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    variants = iter([
        {
            "keyword_rewrite": "ubi pilot labor supply",
            "practitioner_rewrite": "ubi pilot lessons learned employment",
            "contrarian_rewrite": "ubi pilot harms labor market",
            "semantic_description": "A rigorous evaluation of ubi pilot labor-market effects.",
        },
        {
            "keyword_rewrite": "ubi interpretation mixed findings",
            "practitioner_rewrite": "ubi interpretation practitioner critique",
            "contrarian_rewrite": "ubi interpretation alternative explanation",
            "semantic_description": "A careful critique of how mixed ubi results should be interpreted.",
        },
    ])

    async def fake_acall_llm_structured(*args, **kwargs):
        response_model = kwargs["response_model"]
        return response_model(**next(variants)), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr("llm_client.render_prompt", lambda *args, **kwargs: [{"role": "user", "content": "prompt"}])

    queries, query_to_sq, query_counts = await generate_search_queries_tyler_v1(
        _tyler_decomposition(),
        trace_id="test/trace",
    )

    assert len(queries) == 8
    assert query_to_sq["ubi pilot labor supply"] == "Q-1"
    assert query_counts == {"Q-1": 4, "Q-2": 4}


@pytest.mark.asyncio
async def test_build_tyler_evidence_package_uses_tyler_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = EvidenceBundle(
        question=ResearchQuestion(text="What is the current evidence?"),
        sources=[
            SourceRecord(
                id="S-1",
                url="https://example.com/a",
                title="Pilot A",
                source_type="academic",
                quality_tier="authoritative",
                published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                retrieved_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
            ),
            SourceRecord(
                id="S-2",
                url="https://example.com/b",
                title="Pilot B",
                source_type="academic",
                quality_tier="authoritative",
                published_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
                retrieved_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
            ),
        ],
        evidence=[
            EvidenceItem(
                id="E-1",
                source_id="S-1",
                content="Pilot A found a 2 percentage point decline in employment.",
                content_type="quotation",
                sub_question_ids=["Q-1"],
            ),
            EvidenceItem(
                id="E-2",
                source_id="S-2",
                content="Pilot B showed no measurable employment effect.",
                content_type="quotation",
                sub_question_ids=["Q-1"],
            ),
        ],
        gaps=[],
    )

    async def fake_acall_llm_structured(*args, **kwargs):
        response_model = kwargs["response_model"]
        return response_model(
            findings=[
                {
                    "finding": "Pilot evidence was extracted.",
                    "evidence_label": "vendor_documented",
                    "original_quote": "Pilot evidence was extracted.",
                }
            ]
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr("llm_client.render_prompt", lambda *args, **kwargs: [{"role": "user", "content": "prompt"}])

    stage_2 = await build_tyler_evidence_package(
        bundle,
        _tyler_decomposition(),
        trace_id="test/trace",
        query_counts_by_sub_question={"Q-1": 4, "Q-2": 4},
    )

    q1 = next(item for item in stage_2.sub_question_evidence if item.sub_question_id == "Q-1")
    assert len(q1.sources) == 2
    assert q1.meets_sufficiency is True
    assert q1.sources[0].key_findings[0].finding == "Pilot evidence was extracted."
    assert stage_2.queries_per_sub_question["Q-1"] == 4
