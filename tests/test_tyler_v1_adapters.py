"""Tests for staged Tyler V1 adapters."""

from __future__ import annotations

from grounded_research.tyler_v1_adapters import (
    normalize_tyler_decomposition_ids,
    tyler_decomposition_to_current,
)
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


def _tyler_decomposition() -> DecompositionResult:
    return DecompositionResult(
        core_question="What should we recommend?",
        sub_questions=[
            SubQuestion(
                id="bad-1",
                question="What does the evidence show?",
                type="empirical",
                research_priority="high",
                search_guidance="official docs and benchmarks",
            ),
            SubQuestion(
                id="also-bad",
                question="How should the evidence be interpreted?",
                type="interpretive",
                research_priority="medium",
                search_guidance="reviews and case studies",
            ),
        ],
        optimization_axes=["cost vs quality", "speed vs rigor"],
        research_plan=ResearchPlan(
            what_to_verify=["core claim"],
            critical_source_types=["official docs", "benchmarks"],
            falsification_targets=["contradictory production benchmark", "N/A"],
        ),
        stage_summary=_stage_summary(),
    )


def test_normalize_tyler_decomposition_ids_rewrites_non_q_ids() -> None:
    result = _tyler_decomposition()
    normalized = normalize_tyler_decomposition_ids(result)
    assert [sq.id for sq in normalized.sub_questions] == ["Q-1", "Q-2"]


def test_tyler_decomposition_to_current_builds_runtime_compatible_shape() -> None:
    current = tyler_decomposition_to_current(normalize_tyler_decomposition_ids(_tyler_decomposition()))
    assert current.core_question == "What should we recommend?"
    assert len(current.sub_questions) == 2
    assert current.sub_questions[0].text == "What does the evidence show?"
    assert current.sub_questions[0].type == "factual"
    assert current.sub_questions[0].falsification_target == "contradictory production benchmark"
    assert current.sub_questions[1].type == "evaluative"
    assert current.optimization_axes == ["cost vs quality", "speed vs rigor"]
    assert "Verify:" in current.research_plan
