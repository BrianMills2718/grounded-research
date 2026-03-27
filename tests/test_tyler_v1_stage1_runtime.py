"""Tests for Tyler-native Stage 1 runtime migration."""

from __future__ import annotations

import pytest

from grounded_research.decompose import decompose_with_validation_tyler_v1
from grounded_research.models import DecompositionValidation
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
                id="Q-1",
                question="What does the direct evidence show?",
                type="empirical",
                research_priority="high",
                search_guidance="official docs",
            ),
            SubQuestion(
                id="Q-2",
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
async def test_decompose_with_validation_tyler_v1_returns_tyler_and_current(monkeypatch) -> None:
    async def fake_decompose_question_tyler_v1(*args, **kwargs):
        return _decomposition_result()

    async def fake_validate_decomposition(*args, **kwargs):
        return DecompositionValidation(
            coverage_ok=True,
            coverage_gaps=[],
            bias_flags=[],
            granularity_issues=[],
            verdict="proceed",
            revision_guidance="",
        )

    monkeypatch.setattr(
        "grounded_research.decompose.decompose_question_tyler_v1",
        fake_decompose_question_tyler_v1,
    )
    monkeypatch.setattr(
        "grounded_research.decompose.validate_decomposition",
        fake_validate_decomposition,
    )

    tyler_result, current, validation = await decompose_with_validation_tyler_v1(
        question="What should we do?",
        trace_id="test/trace",
    )

    assert tyler_result.sub_questions[0].id == "Q-1"
    assert current.sub_questions[0].text == "What does the direct evidence show?"
    assert validation is not None
    assert validation.verdict == "proceed"


@pytest.mark.asyncio
async def test_decompose_with_validation_tyler_v1_retries_once_on_revision(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_decompose_question_tyler_v1(*args, **kwargs):
        calls.append(kwargs["question"])
        return _decomposition_result()

    validations = iter([
        DecompositionValidation(
            coverage_ok=False,
            coverage_gaps=["gap"],
            bias_flags=[],
            granularity_issues=[],
            verdict="revise",
            revision_guidance="add missing coverage",
        ),
        DecompositionValidation(
            coverage_ok=True,
            coverage_gaps=[],
            bias_flags=[],
            granularity_issues=[],
            verdict="proceed",
            revision_guidance="",
        ),
    ])

    async def fake_validate_decomposition(*args, **kwargs):
        return next(validations)

    monkeypatch.setattr(
        "grounded_research.decompose.decompose_question_tyler_v1",
        fake_decompose_question_tyler_v1,
    )
    monkeypatch.setattr(
        "grounded_research.decompose.validate_decomposition",
        fake_validate_decomposition,
    )

    tyler_result, current, validation = await decompose_with_validation_tyler_v1(
        question="What should we do?",
        trace_id="test/trace",
    )

    assert len(calls) == 2
    assert "Revision guidance" in calls[1]
    assert tyler_result.core_question == "What should we do?"
    assert current.core_question == "What should we do?"
    assert validation is not None
    assert validation.verdict == "proceed"
