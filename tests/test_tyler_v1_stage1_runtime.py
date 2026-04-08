"""Tests for Tyler-native Stage 1 runtime behavior."""

from __future__ import annotations

import pytest

from grounded_research.decompose import decompose_question_tyler_v1
from grounded_research.tyler_v1_models import DecompositionResult, ResearchPlan, StageSummary, SubQuestion


def _stage_summary() -> StageSummary:
    return StageSummary(
        stage_name="Stage 1: Intake & Decomposition",
        goal="goal",
        key_findings=["k1", "k2", "k3"],
        decisions_made=["d1"],
        outcome="outcome",
        reasoning="reasoning",
    )


def _decomposition_result() -> DecompositionResult:
    return DecompositionResult(
        core_question="What should we do?",
        sub_questions=[
            SubQuestion(
                id="1",
                question="What does the direct evidence show?",
                type="empirical",
                research_priority="high",
                search_guidance="official docs",
            ),
            SubQuestion(
                id="2",
                question="How should tradeoffs be interpreted?",
                type="interpretive",
                research_priority="medium",
                search_guidance="reviews",
            ),
        ],
        optimization_axes=["speed vs rigor"],
        research_plan=ResearchPlan(
            what_to_verify=["effect size"],
            critical_source_types=["official docs"],
            falsification_targets=["contradictory benchmark", "N/A"],
        ),
        stage_summary=_stage_summary(),
    )


@pytest.mark.asyncio
async def test_decompose_question_tyler_v1_returns_normalized_tyler_result(monkeypatch) -> None:
    async def fake_acall_llm_structured(*args, **kwargs):
        assert kwargs["task"] == "question_decomposition_tyler_v1"
        return _decomposition_result(), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr("llm_client.render_prompt", lambda *args, **kwargs: [{"role": "user", "content": "prompt"}])

    tyler_result = await decompose_question_tyler_v1(
        question="What should we do?",
        trace_id="test/trace",
    )

    assert tyler_result.sub_questions[0].id == "Q-1"
    assert tyler_result.sub_questions[1].id == "Q-2"
