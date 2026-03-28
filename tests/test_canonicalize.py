"""Tests for Tyler Stage 4 canonicalization and semantic deduplication."""

from __future__ import annotations

import pytest

from grounded_research.canonicalize import canonicalize_tyler_v1, deduplicate_claims
from grounded_research.models import (
    EvidenceBundle,
    EvidenceItem,
    RawClaim,
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


@pytest.mark.asyncio
async def test_dedup_retry_then_fallback_on_invalid_grouping(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid dedup output should retry once, then promote claims 1:1 on failure."""
    # mock-ok: verifies local retry/fallback control flow around the external LLM boundary.
    call_count = 0

    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, timeout):
        nonlocal call_count
        call_count += 1
        assert task == "claim_deduplication"
        assert timeout == 180
        if call_count == 1:
            return response_model(
                groups=[
                    {
                        "canonical_statement": "Merged claim",
                        "raw_claim_ids": ["RC-1", "RC-1"],
                        "confidence": "medium",
                    }
                ]
            ), {}
        return response_model(
            groups=[
                {
                    "canonical_statement": "Still invalid",
                    "raw_claim_ids": ["RC-unknown"],
                    "confidence": "medium",
                }
            ]
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)

    raw_claims = [
        RawClaim(id="RC-1", statement="Claim one", evidence_ids=["E-1"], confidence="high"),
        RawClaim(id="RC-2", statement="Claim two", evidence_ids=["E-2"], confidence="medium"),
    ]
    claim_to_analyst = {"RC-1": "Alpha", "RC-2": "Beta"}

    canonical_claims = await deduplicate_claims(
        raw_claims,
        claim_to_analyst,
        trace_id="test-trace",
        max_budget=0.5,
    )

    assert call_count == 2
    assert len(canonical_claims) == 2
    assert [claim.source_raw_claim_ids for claim in canonical_claims] == [["RC-1"], ["RC-2"]]


@pytest.mark.asyncio
async def test_dedup_retry_accepts_corrected_grouping(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid retry result should be accepted instead of triggering fallback."""
    # mock-ok: verifies local retry acceptance logic around the external LLM boundary.
    call_count = 0

    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, timeout):
        nonlocal call_count
        call_count += 1
        assert task == "claim_deduplication"
        assert timeout == 180
        if call_count == 1:
            return response_model(
                groups=[
                    {
                        "canonical_statement": "Incomplete grouping",
                        "raw_claim_ids": ["RC-1"],
                        "confidence": "medium",
                    }
                ]
            ), {}
        return response_model(
            groups=[
                {
                    "canonical_statement": "Merged claim",
                    "raw_claim_ids": ["RC-1", "RC-2"],
                    "confidence": "high",
                }
            ]
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)

    raw_claims = [
        RawClaim(id="RC-1", statement="Claim one", evidence_ids=["E-1"], confidence="high"),
        RawClaim(id="RC-2", statement="Claim one rephrased", evidence_ids=["E-2"], confidence="medium"),
    ]
    claim_to_analyst = {"RC-1": "Alpha", "RC-2": "Beta"}

    canonical_claims = await deduplicate_claims(
        raw_claims,
        claim_to_analyst,
        trace_id="test-trace",
        max_budget=0.5,
    )

    assert call_count == 2
    assert len(canonical_claims) == 1
    assert canonical_claims[0].source_raw_claim_ids == ["RC-1", "RC-2"]
    assert canonical_claims[0].analyst_sources == ["Alpha", "Beta"] or canonical_claims[0].analyst_sources == ["Beta", "Alpha"]


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


@pytest.mark.asyncio
async def test_canonicalize_tyler_v1_retries_empty_stage4_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 4 should retry with a stronger path when the first result is empty."""
    # mock-ok: verifies local retry/fail-loud logic around an external LLM call.
    calls: list[tuple[str, str]] = []

    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, timeout):
        calls.append((task, model))
        assert timeout == 240
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
    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, timeout):
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

    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, timeout):
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

    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, timeout):
        assert task == "claim_extraction_tyler_v1"
        assert timeout == 240
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


@pytest.mark.asyncio
async def test_dense_dedup_partitions_claims_into_similarity_buckets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dense claim sets should be deduped in smaller semantic buckets."""
    # mock-ok: verifies local staged-partition control flow around the external LLM boundary.
    bucket_calls: list[list[str]] = []

    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, timeout):
        assert task == "claim_deduplication"
        assert timeout == 180
        raw_claim_ids = []
        for message in messages:
            content = message.get("content", "")
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("### RC-"):
                    raw_claim_ids.append(stripped.removeprefix("### ").strip())
        bucket_calls.append(raw_claim_ids)

        if set(raw_claim_ids) == {"RC-1", "RC-2"}:
            return response_model(
                groups=[
                    {
                        "canonical_statement": "Finland's basic income trial showed no employment gain.",
                        "raw_claim_ids": ["RC-1", "RC-2"],
                        "confidence": "high",
                    }
                ]
            ), {}
        if set(raw_claim_ids) == {"RC-3", "RC-4"}:
            return response_model(
                groups=[
                    {
                        "canonical_statement": "Stockton's SEED pilot improved transitions into full-time work.",
                        "raw_claim_ids": ["RC-3", "RC-4"],
                        "confidence": "high",
                    }
                ]
            ), {}

        raise AssertionError(f"Unexpected dedup bucket: {raw_claim_ids}")

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr(
        "grounded_research.canonicalize.get_dedup_config",
        lambda: {
            "staged_trigger_claims": 4,
            "bucket_max_claims": 2,
            "max_doc_frequency_ratio": 0.8,
            "min_shared_informative_tokens": 1,
        },
    )

    raw_claims = [
        RawClaim(
            id="RC-1",
            statement="Finland basic income trial found no employment gain.",
            evidence_ids=["E-1"],
            confidence="high",
        ),
        RawClaim(
            id="RC-2",
            statement="The Finland basic income experiment showed no increase in employment.",
            evidence_ids=["E-2"],
            confidence="medium",
        ),
        RawClaim(
            id="RC-3",
            statement="Stockton SEED improved transitions into full-time work.",
            evidence_ids=["E-3"],
            confidence="high",
        ),
        RawClaim(
            id="RC-4",
            statement="The Stockton pilot increased full-time employment transitions for recipients.",
            evidence_ids=["E-4"],
            confidence="medium",
        ),
    ]
    claim_to_analyst = {
        "RC-1": "Alpha",
        "RC-2": "Beta",
        "RC-3": "Gamma",
        "RC-4": "Alpha",
    }

    canonical_claims = await deduplicate_claims(
        raw_claims,
        claim_to_analyst,
        trace_id="test-trace",
        max_budget=0.5,
    )

    assert len(bucket_calls) == 2
    assert {frozenset(call) for call in bucket_calls} == {
        frozenset({"RC-1", "RC-2"}),
        frozenset({"RC-3", "RC-4"}),
    }
    assert len(canonical_claims) == 2
    assert {frozenset(claim.source_raw_claim_ids) for claim in canonical_claims} == {
        frozenset({"RC-1", "RC-2"}),
        frozenset({"RC-3", "RC-4"}),
    }


@pytest.mark.asyncio
async def test_dense_dedup_split_prefers_shared_evidence_pairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Large semantic components should keep same-evidence claims together."""
    bucket_calls: list[list[str]] = []

    async def fake_acall_llm_structured(
        model,
        messages,
        response_model,
        task,
        trace_id,
        max_budget,
        fallback_models,
        timeout,
    ):
        assert task == "claim_deduplication"
        assert timeout == 180
        raw_claim_ids = []
        for message in messages:
            content = message.get("content", "")
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("### RC-"):
                    raw_claim_ids.append(stripped.removeprefix("### ").strip())
        bucket_calls.append(raw_claim_ids)
        return response_model(
            groups=[
                {
                    "canonical_statement": f"Canonicalized {'/'.join(raw_claim_ids)}",
                    "raw_claim_ids": raw_claim_ids,
                    "confidence": "high",
                }
            ]
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr(
        "grounded_research.canonicalize.get_dedup_config",
        lambda: {
            "staged_trigger_claims": 4,
            "bucket_max_claims": 2,
            "max_doc_frequency_ratio": 0.8,
            "min_shared_informative_tokens": 1,
        },
    )

    raw_claims = [
        RawClaim(
            id="RC-1",
            statement="APFD increased part-time employment by 17%.",
            evidence_ids=["E-1"],
            confidence="high",
        ),
        RawClaim(
            id="RC-2",
            statement="The Alaska Permanent Fund Dividend increased part-time employment by 17%.",
            evidence_ids=["E-1"],
            confidence="medium",
        ),
        RawClaim(
            id="RC-3",
            statement="APFD showed no significant full-time employment effect.",
            evidence_ids=["E-2"],
            confidence="high",
        ),
        RawClaim(
            id="RC-4",
            statement="The Alaska Permanent Fund Dividend showed no significant full-time employment effect.",
            evidence_ids=["E-2"],
            confidence="medium",
        ),
    ]
    claim_to_analyst = {
        "RC-1": "Alpha",
        "RC-2": "Beta",
        "RC-3": "Gamma",
        "RC-4": "Alpha",
    }

    canonical_claims = await deduplicate_claims(
        raw_claims,
        claim_to_analyst,
        trace_id="test-trace",
        max_budget=0.5,
    )

    assert {frozenset(call) for call in bucket_calls} == {
        frozenset({"RC-1", "RC-2"}),
        frozenset({"RC-3", "RC-4"}),
    }
    assert {frozenset(claim.source_raw_claim_ids) for claim in canonical_claims} == {
        frozenset({"RC-1", "RC-2"}),
        frozenset({"RC-3", "RC-4"}),
    }
