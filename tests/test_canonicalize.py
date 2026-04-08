"""Tests for Tyler Stage 4 canonicalization."""

from __future__ import annotations

import random

import pytest

from grounded_research.canonicalize import (
    _randomize_stage4_analysis_order,
    canonicalize_tyler_v1,
)
from grounded_research.models import (
    EvidenceBundle,
    EvidenceItem,
    ResearchQuestion,
    SourceRecord,
)
from grounded_research.tyler_v1_models import (
    AnalysisObject,
    ClaimExtractionResult,
    Claim as TylerClaim,
    ConfidenceLevel,
    CounterArgument,
    DecompositionResult,
    ResearchPlan,
    StageSummary,
    SubQuestion as TylerSubQuestion,
    Assumption as TylerAssumption,
)


def _tyler_stage4_bundle() -> EvidenceBundle:
    """Fixture bundle for Tyler Stage 4 runtime retry tests."""
    return EvidenceBundle(
        question=ResearchQuestion(text="Should teams use Redis or PostgreSQL for session storage?"),
        sources=[
            SourceRecord(
                id="S-1",
                url="https://example.com/redis-benchmark",
                title="Redis benchmark",
                source_type="academic",
                quality_tier="authoritative",
            ),
            SourceRecord(
                id="S-2",
                url="https://example.com/postgres-durability",
                title="PostgreSQL durability",
                source_type="academic",
                quality_tier="authoritative",
            ),
        ],
        evidence=[
            EvidenceItem(id="E-1", source_id="S-1", content="Redis had lower p99 latency.", content_type="text"),
            EvidenceItem(id="E-2", source_id="S-2", content="PostgreSQL preserved sessions via WAL replay.", content_type="text"),
        ],
    )


def _tyler_stage4_stage1_result() -> DecompositionResult:
    """Fixture Tyler Stage 1 artifact for Stage 4 runtime tests."""
    return DecompositionResult(
        core_question="Should teams use Redis or PostgreSQL for session storage?",
        sub_questions=[
            TylerSubQuestion(
                id="Q-1",
                question="What are the latency and throughput differences?",
                type="interpretive",
                research_priority="high",
                search_guidance="benchmarks and performance evaluations",
            ),
            TylerSubQuestion(
                id="Q-2",
                question="What durability tradeoffs matter for session storage?",
                type="interpretive",
                research_priority="medium",
                search_guidance="crash recovery and durability evidence",
            ),
        ],
        optimization_axes=["latency vs durability"],
        research_plan=ResearchPlan(
            what_to_verify=["latency tradeoffs", "durability tradeoffs"],
            critical_source_types=["benchmarks", "vendor docs"],
            falsification_targets=[
                "PostgreSQL matches Redis on latency.",
                "Redis matches PostgreSQL on durability.",
            ],
        ),
        stage_summary=StageSummary(
            stage_name="Stage 1",
            goal="goal",
            key_findings=["k1", "k2", "k3"],
            decisions_made=["d1"],
            outcome="outcome",
            reasoning="reasoning",
        ),
    )


def _tyler_stage4_analysis_objects() -> tuple[list[AnalysisObject], dict[str, str]]:
    """Build canonical Tyler Stage 3 fixtures without compatibility projections."""
    return [
        AnalysisObject(
            model_alias="A",
            reasoning_frame="verification_first",
            recommendation="Prefer Redis when latency is primary.",
            claims=[
                TylerClaim(
                    id="C-1",
                    statement="Redis achieved lower p99 latency than PostgreSQL for session reads.",
                    evidence_label="vendor_documented",
                    source_references=["S-1"],
                    confidence=ConfidenceLevel.HIGH,
                )
            ],
            assumptions=[],
            evidence_used=["S-1"],
            counter_argument=CounterArgument(
                argument="Durability may matter more than latency.",
                strongest_evidence_against="PostgreSQL preserved sessions via WAL replay.",
                counter_confidence=ConfidenceLevel.MEDIUM,
            ),
            falsification_conditions=["Durability requirements outweigh latency benefits."],
            reasoning="Redis is lower-latency.",
            stage_summary=StageSummary(
                stage_name="Stage 3",
                goal="goal",
                key_findings=["k1", "k2", "k3"],
                decisions_made=["d1"],
                outcome="outcome",
                reasoning="reasoning",
            ),
        ),
        AnalysisObject(
            model_alias="B",
            reasoning_frame="structured_decomposition",
            recommendation="Prefer PostgreSQL when durability dominates.",
            claims=[
                TylerClaim(
                    id="C-1",
                    statement="PostgreSQL preserved sessions across crash recovery via WAL replay.",
                    evidence_label="vendor_documented",
                    source_references=["S-2"],
                    confidence=ConfidenceLevel.HIGH,
                )
            ],
            assumptions=[
                TylerAssumption(
                    id="A-1",
                    statement="Crash recovery matters for this workload.",
                    depends_on_claims=["C-1"],
                    if_wrong_impact="The durability recommendation weakens.",
                )
            ],
            evidence_used=["S-2"],
            counter_argument=CounterArgument(
                argument="Latency is materially higher than Redis.",
                strongest_evidence_against="Redis had lower p99 latency.",
                counter_confidence=ConfidenceLevel.MEDIUM,
            ),
            falsification_conditions=["Latency dominates crash-recovery needs."],
            reasoning="PostgreSQL is more durable.",
            stage_summary=StageSummary(
                stage_name="Stage 3",
                goal="goal",
                key_findings=["k1", "k2", "k3"],
                decisions_made=["d1"],
                outcome="outcome",
                reasoning="reasoning",
            ),
        ),
    ], {"Alpha": "A", "Beta": "B"}


def test_randomize_stage4_analysis_order_preserves_aliases_without_mutating_input() -> None:
    """Stage 4 shuffling should reorder a copy, not mutate the caller-owned list."""
    stage_3_results, _alias_mapping = _tyler_stage4_analysis_objects()

    randomized = _randomize_stage4_analysis_order(stage_3_results, rng=random.Random(1))

    assert [analysis.model_alias for analysis in randomized] == ["B", "A"]
    assert sorted(analysis.model_alias for analysis in randomized) == ["A", "B"]
    assert [analysis.model_alias for analysis in stage_3_results] == ["A", "B"]


@pytest.mark.asyncio
async def test_canonicalize_tyler_v1_randomizes_stage4_prompt_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 4 prompt rendering should consume the randomized analyst order."""
    captured_orders: list[list[str]] = []

    def fake_render_prompt(*args, **kwargs):
        captured_orders.append([entry["model_alias"] for entry in kwargs["stage_3_results"]])
        return [{"role": "user", "content": "prompt"}]

    async def fake_acall_llm_structured(*args, **kwargs):
        response_model = kwargs["response_model"]
        return response_model.model_validate(
            {
                "claim_ledger": [],
                "assumption_set": [],
                "dispute_queue": [],
                "statistics": {
                    "total_claims": 0,
                    "total_assumptions": 0,
                    "total_disputes": 0,
                    "disputes_by_type": {},
                    "decision_critical_disputes": 0,
                    "claims_per_model": {},
                },
                "stage_summary": {
                    "stage_name": "Stage 4",
                    "goal": "goal",
                    "key_findings": ["empty"],
                    "decisions_made": ["returned empty"],
                    "outcome": "outcome",
                    "reasoning": "reasoning",
                },
            }
        ), {}

    monkeypatch.setattr("llm_client.render_prompt", fake_render_prompt)
    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr(
        "grounded_research.canonicalize._randomize_stage4_analysis_order",
        lambda stage_3_results: [stage_3_results[1], stage_3_results[0]],
    )
    monkeypatch.setattr(
        "grounded_research.canonicalize.get_tyler_literal_parity_config",
        lambda: {"stage4_retry_on_empty_claims": False},
    )

    stage_3_results, alias_mapping = _tyler_stage4_analysis_objects()
    await canonicalize_tyler_v1(
        _tyler_stage4_bundle(),
        tyler_stage_1_result=_tyler_stage4_stage1_result(),
        tyler_stage_3_results=stage_3_results,
        tyler_stage_3_alias_mapping=alias_mapping,
        trace_id="trace-randomized",
        max_budget=0.5,
    )

    assert captured_orders == [["B", "A"]]


@pytest.mark.asyncio
async def test_canonicalize_tyler_v1_rerenders_retry_from_fresh_randomized_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry calls should re-render Stage 4 input instead of reusing fixed-order messages."""
    captured_orders: list[list[str]] = []
    randomized_orders = iter((["B", "A"], ["A", "B"]))

    def fake_render_prompt(*args, **kwargs):
        captured_orders.append([entry["model_alias"] for entry in kwargs["stage_3_results"]])
        return [{"role": "user", "content": "prompt"}]

    async def fake_acall_llm_structured(*args, **kwargs):
        response_model = kwargs["response_model"]
        task = kwargs["task"]
        if task == "claim_extraction_tyler_v1":
            return response_model.model_validate(
                {
                    "claim_ledger": [],
                    "assumption_set": [],
                    "dispute_queue": [],
                    "statistics": {
                        "total_claims": 0,
                        "total_assumptions": 0,
                        "total_disputes": 0,
                        "disputes_by_type": {},
                        "decision_critical_disputes": 0,
                        "claims_per_model": {},
                    },
                    "stage_summary": {
                        "stage_name": "Stage 4",
                        "goal": "goal",
                        "key_findings": ["empty"],
                        "decisions_made": ["returned empty"],
                        "outcome": "outcome",
                        "reasoning": "reasoning",
                    },
                }
            ), {}
        return response_model.model_validate(
            {
                "claim_ledger": [
                    {
                        "id": "C-1",
                        "statement": "Redis achieved lower p99 latency than PostgreSQL for session reads.",
                        "source_models": ["A"],
                        "evidence_label": "empirically_observed",
                        "source_references": ["S-1"],
                        "status": "supported",
                        "supporting_models": ["A"],
                        "contesting_models": ["B"],
                        "related_assumptions": [],
                    }
                ],
                "assumption_set": [],
                "dispute_queue": [],
                "statistics": {
                    "total_claims": 1,
                    "total_assumptions": 0,
                    "total_disputes": 0,
                    "disputes_by_type": {},
                    "decision_critical_disputes": 0,
                    "claims_per_model": {"A": 1},
                },
                "stage_summary": {
                    "stage_name": "Stage 4",
                    "goal": "goal",
                    "key_findings": ["k1", "k2", "k3"],
                    "decisions_made": ["d1"],
                    "outcome": "outcome",
                    "reasoning": "reasoning",
                },
            }
        ), {}

    monkeypatch.setattr("llm_client.render_prompt", fake_render_prompt)
    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr(
        "grounded_research.canonicalize._randomize_stage4_analysis_order",
        lambda stage_3_results: [
            next_alias for alias in next(randomized_orders)
            for next_alias in stage_3_results
            if next_alias.model_alias == alias
        ],
    )
    monkeypatch.setattr(
        "grounded_research.canonicalize.get_tyler_literal_parity_config",
        lambda: {
            "stage4_retry_on_empty_claims": True,
            "stage4_retry_model": "openrouter/google/gemini-2.5-flash",
            "stage4_retry_fallback_models": None,
        },
    )

    stage_3_results, alias_mapping = _tyler_stage4_analysis_objects()
    result = await canonicalize_tyler_v1(
        _tyler_stage4_bundle(),
        tyler_stage_1_result=_tyler_stage4_stage1_result(),
        tyler_stage_3_results=stage_3_results,
        tyler_stage_3_alias_mapping=alias_mapping,
        trace_id="trace-retry",
        max_budget=0.5,
    )

    assert [claim.id for claim in result.claim_ledger] == ["C-1"]
    assert captured_orders == [["B", "A"], ["A", "B"]]


@pytest.mark.asyncio
async def test_canonicalize_tyler_v1_retries_empty_stage4_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 4 should retry with a stronger path when the first result is empty."""
    # mock-ok: verifies local retry/fail-loud logic around an external LLM call.
    calls: list[tuple[str, str]] = []

    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, **kwargs):
        calls.append((task, model))
        assert "timeout" not in kwargs
        if task == "claim_extraction_tyler_v1":
            return response_model.model_validate(
                {
                    "claim_ledger": [],
                    "assumption_set": [],
                    "dispute_queue": [],
                    "statistics": {
                        "total_claims": 0,
                        "total_assumptions": 0,
                        "total_disputes": 0,
                        "disputes_by_type": {},
                        "decision_critical_disputes": 0,
                        "claims_per_model": {},
                    },
                    "stage_summary": {
                        "stage_name": "Stage 4",
                        "goal": "goal",
                        "key_findings": ["empty"],
                        "decisions_made": ["returned empty"],
                        "outcome": "outcome",
                        "reasoning": "reasoning",
                    },
                }
            ), {}
        assert task == "claim_extraction_tyler_v1_retry"
        assert model == "openrouter/google/gemini-2.5-flash"
        return response_model.model_validate(
            {
                "claim_ledger": [
                    {
                        "id": "C-bad",
                        "statement": "Redis achieved lower p99 latency than PostgreSQL for session reads.",
                        "source_models": ["A"],
                        "evidence_label": "empirically_observed",
                        "source_references": ["S-1"],
                        "status": "supported",
                        "supporting_models": ["A"],
                        "contesting_models": ["B"],
                        "related_assumptions": [],
                    }
                ],
                "assumption_set": [],
                "dispute_queue": [],
                "statistics": {
                    "total_claims": 1,
                    "total_assumptions": 0,
                    "total_disputes": 0,
                    "disputes_by_type": {},
                    "decision_critical_disputes": 0,
                    "claims_per_model": {"A": 1},
                },
                "stage_summary": {
                    "stage_name": "Stage 4",
                    "goal": "goal",
                    "key_findings": ["retry succeeded"],
                    "decisions_made": ["kept one claim"],
                    "outcome": "outcome",
                    "reasoning": "reasoning",
                },
            }
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    analyses, alias_mapping = _tyler_stage4_analysis_objects()

    result = await canonicalize_tyler_v1(
        _tyler_stage4_bundle(),
        tyler_stage_1_result=_tyler_stage4_stage1_result(),
        tyler_stage_3_results=analyses,
        tyler_stage_3_alias_mapping=alias_mapping,
        trace_id="test-trace",
        max_budget=0.5,
    )

    assert [task for task, _model in calls] == [
        "claim_extraction_tyler_v1",
        "claim_extraction_tyler_v1_retry",
    ]
    assert len(result.claim_ledger) == 1


@pytest.mark.asyncio
async def test_canonicalize_tyler_v1_fails_loud_on_persistent_empty_stage4(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 4 should fail loud if both the primary call and retry remain empty."""
    # mock-ok: verifies local fail-loud guard around an external LLM call.
    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, **kwargs):
        return response_model.model_validate(
            {
                "claim_ledger": [],
                "assumption_set": [],
                "dispute_queue": [],
                "statistics": {
                    "total_claims": 0,
                    "total_assumptions": 0,
                    "total_disputes": 0,
                    "disputes_by_type": {},
                    "decision_critical_disputes": 0,
                    "claims_per_model": {},
                },
                "stage_summary": {
                    "stage_name": "Stage 4",
                    "goal": "goal",
                    "key_findings": ["empty"],
                    "decisions_made": ["returned empty"],
                    "outcome": "outcome",
                    "reasoning": "reasoning",
                },
            }
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    analyses, alias_mapping = _tyler_stage4_analysis_objects()

    with pytest.raises(ValueError, match="empty claim ledger and assumption set after retry"):
        await canonicalize_tyler_v1(
            _tyler_stage4_bundle(),
            tyler_stage_1_result=_tyler_stage4_stage1_result(),
            tyler_stage_3_results=analyses,
            tyler_stage_3_alias_mapping=alias_mapping,
            trace_id="test-trace",
            max_budget=0.5,
        )


@pytest.mark.asyncio
async def test_canonicalize_tyler_v1_retries_stage4_after_schema_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 4 should retry with the stronger path after a schema failure."""
    # mock-ok: verifies local retry behavior after an external LLM schema failure.
    calls: list[tuple[str, str]] = []

    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, **kwargs):
        calls.append((task, model))
        if task == "claim_extraction_tyler_v1":
            raise ValueError("dispute_queue missing; assumption_set contains dispute objects")
        assert task == "claim_extraction_tyler_v1_retry"
        assert model == "openrouter/google/gemini-2.5-flash"
        return response_model.model_validate(
            {
                "claim_ledger": [
                    {
                        "id": "C-1",
                        "statement": "Redis achieved lower p99 latency than PostgreSQL for session reads.",
                        "source_models": ["A"],
                        "evidence_label": "empirically_observed",
                        "source_references": ["S-1"],
                        "status": "supported",
                        "supporting_models": ["A"],
                        "contesting_models": [],
                        "related_assumptions": [],
                    }
                ],
                "assumption_set": [],
                "dispute_queue": [],
                "statistics": {
                    "total_claims": 1,
                    "total_assumptions": 0,
                    "total_disputes": 0,
                    "disputes_by_type": {},
                    "decision_critical_disputes": 0,
                    "claims_per_model": {"A": 1},
                },
                "stage_summary": {
                    "stage_name": "Stage 4",
                    "goal": "goal",
                    "key_findings": ["retry succeeded after schema failure"],
                    "decisions_made": ["kept one claim"],
                    "outcome": "outcome",
                    "reasoning": "reasoning",
                },
            }
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    analyses, alias_mapping = _tyler_stage4_analysis_objects()

    result = await canonicalize_tyler_v1(
        _tyler_stage4_bundle(),
        tyler_stage_1_result=_tyler_stage4_stage1_result(),
        tyler_stage_3_results=analyses,
        tyler_stage_3_alias_mapping=alias_mapping,
        trace_id="test-trace",
        max_budget=0.5,
    )

    assert [task for task, _model in calls] == [
        "claim_extraction_tyler_v1",
        "claim_extraction_tyler_v1_retry",
    ]
    assert len(result.claim_ledger) == 1


@pytest.mark.asyncio
async def test_canonicalize_tyler_v1_live_path_requires_only_tyler_stage3_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The live Stage 4 path should work from Tyler Stage 3 artifacts alone."""
    analyses, alias_mapping = _tyler_stage4_analysis_objects()

    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, **kwargs):
        assert task == "claim_extraction_tyler_v1"
        assert "timeout" not in kwargs
        return response_model.model_validate(
            {
                "claim_ledger": [
                    {
                        "id": "C-1",
                        "statement": "Redis achieved lower p99 latency than PostgreSQL for session reads.",
                        "source_models": ["A"],
                        "evidence_label": "empirically_observed",
                        "source_references": ["S-1"],
                        "status": "supported",
                        "supporting_models": ["A"],
                        "contesting_models": ["B"],
                        "related_assumptions": [],
                    }
                ],
                "assumption_set": [],
                "dispute_queue": [],
                "statistics": {
                    "total_claims": 1,
                    "total_assumptions": 0,
                    "total_disputes": 0,
                    "disputes_by_type": {},
                    "decision_critical_disputes": 0,
                    "claims_per_model": {"A": 1, "B": 1},
                },
                "stage_summary": {
                    "stage_name": "Stage 4",
                    "goal": "goal",
                    "key_findings": ["k1"],
                    "decisions_made": ["d1"],
                    "outcome": "outcome",
                    "reasoning": "reasoning",
                },
            }
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)

    result = await canonicalize_tyler_v1(
        _tyler_stage4_bundle(),
        tyler_stage_1_result=_tyler_stage4_stage1_result(),
        tyler_stage_3_results=analyses,
        tyler_stage_3_alias_mapping=alias_mapping,
        trace_id="test-trace",
        max_budget=0.5,
    )

    assert len(result.claim_ledger) == 1
    assert result.claim_ledger[0].id == "C-1"
