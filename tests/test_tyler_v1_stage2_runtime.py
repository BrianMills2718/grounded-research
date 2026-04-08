"""Tests for Tyler-native Stage 2 runtime behavior."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from grounded_research.collect import build_tyler_evidence_package, generate_search_queries_tyler_v1
from grounded_research.models import (
    EvidenceBundle,
    EvidenceItem,
    ResearchQuestion,
    SourceRecord,
)
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
async def test_generate_search_queries_tyler_v1_returns_routed_query_plans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tyler Stage 2 should emit typed query plans from the lightweight prompt."""

    async def fake_acall_llm_structured(*args, **kwargs):
        response_model = kwargs["response_model"]
        return response_model(
            keyword_rewrite="pilot A employment effect",
            practitioner_rewrite="pilot A lessons learned",
            contrarian_falsification="pilot A limitations contradiction",
            semantic_description="A detailed evaluation of pilot A with direct labor-market outcomes.",
            reasoning="Distinct keyword, practitioner, contrarian, and semantic retrieval vectors.",
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr("llm_client.render_prompt", lambda *args, **kwargs: [{"role": "user", "content": "prompt"}])

    query_plans, query_counts = await generate_search_queries_tyler_v1(
        _tyler_decomposition(),
        trace_id="test/trace",
    )

    assert query_counts["Q-1"] == 4
    assert query_counts["Q-2"] == 3
    assert [plan.provider for plan in query_plans if plan.sub_question_id == "Q-1"] == [
        "tavily", "tavily", "tavily", "exa",
    ]
    assert [plan.query_role for plan in query_plans if plan.sub_question_id == "Q-1"] == [
        "keyword_rewrite",
        "practitioner_rewrite",
        "contrarian_falsification",
        "semantic_description",
    ]
    assert all(plan.search_depth == "basic" for plan in query_plans if plan.provider == "tavily")
    assert all(plan.result_detail == "chunks" for plan in query_plans if plan.provider == "exa")
    exa_plan = next(plan for plan in query_plans if plan.provider == "exa")
    assert exa_plan.retrieval_instruction == "Prioritize sources aligned with this guidance: official reports and evaluations."


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


@pytest.mark.asyncio
async def test_build_tyler_evidence_package_translates_legacy_fixture_sub_question_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
                sub_question_ids=["SQ-alpha"],
            ),
            EvidenceItem(
                id="E-2",
                source_id="S-2",
                content="Pilot B showed no measurable employment effect.",
                content_type="quotation",
                sub_question_ids=["SQ-alpha"],
            ),
        ],
        gaps=[],
    )

    async def fake_acall_llm_structured(*args, **kwargs):
        response_model = kwargs["response_model"]
        return response_model(
            findings=[
                {
                    "finding": "Legacy fixture evidence was translated.",
                    "evidence_label": "vendor_documented",
                    "original_quote": "Legacy fixture evidence was translated.",
                }
            ]
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr("llm_client.render_prompt", lambda *args, **kwargs: [{"role": "user", "content": "prompt"}])

    with pytest.raises(ValueError, match="requires Tyler Stage 1 sub-question IDs"):
        await build_tyler_evidence_package(
            bundle,
            _tyler_decomposition(),
            trace_id="test/trace",
            query_counts_by_sub_question={"Q-1": 4, "Q-2": 4},
        )
