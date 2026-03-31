"""Tests for arbitration protocol enforcement and verification wiring.

These tests exercise the local anti-conformity validation layer around
arbitration output. The LLM boundary is mocked elsewhere; here we verify that
live claim-status changes only survive when they are tied to structured fresh
evidence support.
"""

from __future__ import annotations

import json

import pytest

from grounded_research.models import (
    EvidenceBundle,
    EvidenceItem,
    ResearchQuestion,
    SourceRecord,
)
from grounded_research.verify import (
    _collect_fresh_evidence_for_dispute,
    _build_tyler_verification_queries,
    arbitrate_dispute_tyler_v1,
    verify_disputes_tyler_v1,
)
from grounded_research.tyler_v1_models import (
    ClaimExtractionResult as TylerClaimExtractionResult,
    ClaimLedgerEntry,
    ClaimStatus as TylerClaimStatus,
    DecompositionResult,
    DisputeQueueEntry,
    DisputeStatus,
    DisputeType,
    EvidencePackage,
    EvidenceLabel,
    ResearchPlan,
    ResolutionOutcome,
    Source as TylerSource,
    StageSummary,
    SubQuestion,
)


def test_build_tyler_verification_queries_matches_literal_query_roles() -> None:
    """Stage 5 should emit neutral, weaker-position, and authoritative queries."""
    dispute = DisputeQueueEntry(
        id="D-1",
        type=DisputeType.EMPIRICAL,
        description="Whether employment changed",
        claims_involved=["C-1", "C-2"],
        model_positions=[],
        decision_critical=True,
        decision_critical_rationale="Could change the recommendation.",
        status=DisputeStatus.UNRESOLVED,
        resolution_routing="stage_5_evidence",
    )
    claim_entries = [
        ClaimLedgerEntry(
            id="C-1",
            statement="Employment stayed flat in the pilot",
            source_models=["A", "B"],
            evidence_label=EvidenceLabel.EMPIRICALLY_OBSERVED,
            source_references=["S-1"],
            status=TylerClaimStatus.CONTESTED,
            supporting_models=["A", "B"],
            contesting_models=["C"],
            related_assumptions=[],
        ),
        ClaimLedgerEntry(
            id="C-2",
            statement="Employment declined after the pilot",
            source_models=["C"],
            evidence_label=EvidenceLabel.EMPIRICALLY_OBSERVED,
            source_references=["S-2"],
            status=TylerClaimStatus.CONTESTED,
            supporting_models=["C"],
            contesting_models=["A", "B"],
            related_assumptions=[],
        ),
    ]
    relevant_original_sources = [
        TylerSource(
            id="S-2",
            url="https://oecd.org/reports/pilot-labor-study",
            title="Pilot labor study",
            source_type="academic",
            quality_score=0.91,
            publication_date="2025-10-01",
            retrieval_date="2026-03-30",
            key_findings=[],
        )
    ]

    queries = _build_tyler_verification_queries(
        dispute=dispute,
        claim_entries=claim_entries,
        relevant_original_sources=relevant_original_sources,
        original_query="Should cities adopt UBI pilots?",
        time_sensitivity="mixed",
    )

    # Tyler V1 spec: neutral, [topic] limitations, [leading claim] contradicted by
    assert queries[0] == "Did employment change?"
    assert queries[1] == "employment change limitations"
    assert queries[2] == "Employment stayed flat in the pilot contradicted by"
    assert len(queries) == 3


def test_build_tyler_verification_queries_adds_dated_search_only_when_time_sensitive() -> None:
    """Time-sensitive disputes should add the Tyler-style dated authoritative query."""
    dispute = DisputeQueueEntry(
        id="D-1",
        type=DisputeType.INTERPRETIVE,
        description="How regulators interpret the new rule",
        claims_involved=["C-1"],
        model_positions=[],
        decision_critical=True,
        decision_critical_rationale="Could change the recommendation.",
        status=DisputeStatus.UNRESOLVED,
        resolution_routing="stage_5_arbitration",
    )
    claim_entries = [
        ClaimLedgerEntry(
            id="C-1",
            statement="Regulators prefer a broad reading of the rule",
            source_models=["A"],
            evidence_label=EvidenceLabel.VENDOR_DOCUMENTED,
            source_references=["S-1"],
            status=TylerClaimStatus.CONTESTED,
            supporting_models=["A"],
            contesting_models=[],
            related_assumptions=[],
        )
    ]

    queries = _build_tyler_verification_queries(
        dispute=dispute,
        claim_entries=claim_entries,
        relevant_original_sources=[],
        original_query="How should we interpret the rule?",
        time_sensitivity="time_sensitive",
    )

    # Tyler V1 spec: neutral, limitations, refutation, + dated authoritative for time_sensitive
    assert len(queries) == 4
    assert queries[0] == "What does the evidence show about how regulators interpret the new rule?"
    assert queries[1] == "How regulators interpret the new rule limitations"
    assert queries[2] == "Regulators prefer a broad reading of the rule contradicted by"
    assert queries[3].endswith(" 2026")


@pytest.mark.asyncio
async def test_arbitrate_dispute_tyler_v1_passes_configured_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live Tyler Stage 5 arbitration should use the configured finite timeout."""
    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, timeout):
        assert task == "dispute_arbitration_tyler_v1"
        assert timeout == 240
        return response_model(
            dispute_id="D-1",
            resolution=ResolutionOutcome.EVIDENCE_INSUFFICIENT,
            updated_claim_statuses=[],
            new_evidence_summary="No fresh evidence materially changed the claim.",
            reasoning="No fresh evidence materially changed the claim.",
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr("llm_client.render_prompt", lambda *args, **kwargs: [{"role": "user", "content": "prompt"}])

    dispute = DisputeQueueEntry(
        id="D-1",
        type=DisputeType.EMPIRICAL,
        description="Conflicting evidence about the same factual question.",
        claims_involved=["C-1", "C-2"],
        model_positions=[],
        decision_critical=True,
        decision_critical_rationale="Could change answer.",
        status=DisputeStatus.UNRESOLVED,
        resolution_routing="stage_5_evidence",
    )
    claim_ledger = [
        ClaimLedgerEntry(
            id="C-1",
            statement="Claim 1",
            source_models=["A"],
            evidence_label=EvidenceLabel.EMPIRICALLY_OBSERVED,
            source_references=["S-1"],
            status=TylerClaimStatus.CONTESTED,
            supporting_models=["A"],
            contesting_models=["B"],
            related_assumptions=[],
        ),
        ClaimLedgerEntry(
            id="C-2",
            statement="Claim 2",
            source_models=["B"],
            evidence_label=EvidenceLabel.EMPIRICALLY_OBSERVED,
            source_references=["S-2"],
            status=TylerClaimStatus.CONTESTED,
            supporting_models=["B"],
            contesting_models=["A"],
            related_assumptions=[],
        ),
    ]

    result = await arbitrate_dispute_tyler_v1(
        original_query="What is the evidence?",
        dispute=dispute,
        claim_ledger_entries=claim_ledger,
        relevant_original_sources=[],
        new_evidence=[],
        trace_id="trace-1",
        max_budget=0.5,
    )

    assert result.dispute_id == "D-1"
    assert result.resolution is ResolutionOutcome.EVIDENCE_INSUFFICIENT


@pytest.mark.asyncio
async def test_collect_fresh_evidence_uses_verification_search_trace_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verification-time search should propagate trace metadata for observability."""
    captured: dict[str, str | None] = {}

    async def fake_search_web(query: str, count: int = 10, freshness: str = "none", *, trace_id=None, task=None):
        captured["trace_id"] = trace_id
        captured["task"] = task
        return json.dumps({"results": []})

    monkeypatch.setattr("grounded_research.tools.web_search.search_web", fake_search_web)

    bundle = EvidenceBundle(
        question=ResearchQuestion(text="What is the evidence?"),
        sources=[],
        evidence=[],
        gaps=[],
    )

    _sources, _evidence, warnings = await _collect_fresh_evidence_for_dispute(
        dispute_id="D-1",
        queries=["test query"],
        bundle=bundle,
        trace_id="trace-root",
    )

    assert captured["trace_id"] == "trace-root/search/D-1"
    assert captured["task"] == "verification.search"
    assert any(w.code == "verification_no_results" for w in warnings)


@pytest.mark.asyncio
async def test_verify_disputes_tyler_v1_updates_stage5_artifact_without_compat_ledger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tyler Stage 5 should update only the canonical verification artifact."""
    monkeypatch.setattr("grounded_research.verify.get_depth_config", lambda: {"arbitration_max_rounds": 1})

    async def fake_decompose_question_tyler_v1(question: str, trace_id: str, max_budget: float = 0.5):
        from grounded_research.tyler_v1_models import DecompositionResult, ResearchPlan, StageSummary, SubQuestion

        return DecompositionResult(
            core_question=question,
            sub_questions=[
                SubQuestion(
                    id="Q-1",
                    question="What happened in the pilot?",
                    type="empirical",
                    research_priority="high",
                    search_guidance="official evaluations",
                ),
                SubQuestion(
                    id="Q-2",
                    question="How should policymakers interpret the pilot?",
                    type="interpretive",
                    research_priority="medium",
                    search_guidance="policy analysis",
                ),
            ],
            optimization_axes=["risk vs upside"],
            research_plan=ResearchPlan(
                what_to_verify=["employment effects"],
                critical_source_types=["official evaluations"],
                falsification_targets=["evidence of harm"],
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

    async def fake_collect(dispute_id, queries, bundle, trace_id):
        source = SourceRecord(url="https://example.com/fresh", title="Fresh source")
        evidence = EvidenceItem(
            source_id=source.id,
            content="Fresh evidence",
            content_type="text",
            relevance_note="fresh",
            extraction_method="llm",
        )
        return [source], [evidence], []

    async def fake_arbitrate(**kwargs):
        from grounded_research.tyler_v1_models import ArbitrationAssessment, ClaimStatusUpdate

        return ArbitrationAssessment(
            dispute_id="D-1",
            new_evidence_summary="Fresh evidence favored C-1.",
            reasoning="Reasoning",
            resolution=ResolutionOutcome.CLAIM_SUPPORTED,
            updated_claim_statuses=[
                ClaimStatusUpdate(
                    claim_id="C-1",
                    new_status=TylerClaimStatus.VERIFIED,
                    confidence_in_resolution="high",
                    remaining_uncertainty=None,
                )
            ],
        )

    monkeypatch.setattr("grounded_research.decompose.decompose_question_tyler_v1", fake_decompose_question_tyler_v1)
    monkeypatch.setattr("grounded_research.verify._collect_fresh_evidence_for_dispute", fake_collect)
    monkeypatch.setattr("grounded_research.verify.arbitrate_dispute_tyler_v1", fake_arbitrate)

    stage_4_result = TylerClaimExtractionResult(
        claim_ledger=[
            ClaimLedgerEntry(
                id="C-1",
                statement="Employment stayed flat.",
                source_models=["A"],
                evidence_label=EvidenceLabel.EMPIRICALLY_OBSERVED,
                source_references=["S-1"],
                status=TylerClaimStatus.CONTESTED,
                supporting_models=["A"],
                contesting_models=["B"],
                related_assumptions=[],
            )
        ],
        assumption_set=[],
        dispute_queue=[
            DisputeQueueEntry(
                id="D-1",
                type=DisputeType.EMPIRICAL,
                description="Whether employment changed.",
                claims_involved=["C-1"],
                model_positions=[],
                decision_critical=True,
                decision_critical_rationale="Could change answer.",
                status=DisputeStatus.UNRESOLVED,
                resolution_routing="stage_5_evidence",
            )
        ],
        statistics={
            "total_claims": 1,
            "total_assumptions": 0,
            "total_disputes": 1,
            "disputes_by_type": {"empirical": 1},
            "decision_critical_disputes": 1,
            "claims_per_model": {"A": 1},
        },
        stage_summary={
            "stage_name": "Stage 4",
            "goal": "goal",
            "key_findings": ["k1", "k2", "k3"],
            "decisions_made": ["d1"],
            "outcome": "outcome",
            "reasoning": "reasoning",
        },
    )
    bundle = EvidenceBundle(
        question=ResearchQuestion(text="Should cities adopt UBI pilots?"),
        sources=[SourceRecord(id="S-1", url="https://example.com/source", title="Source")],
        evidence=[EvidenceItem(id="E-1", source_id="S-1", content="Base evidence", content_type="text")],
        gaps=[],
    )
    stage_2_result = EvidencePackage(
        sub_question_evidence=[],
        total_queries_used=0,
        queries_per_sub_question={"Q-1": 0, "Q-2": 0},
        stage_summary=StageSummary(
            stage_name="Stage 2",
            goal="goal",
            key_findings=["k1", "k2", "k3"],
            decisions_made=["d1"],
            outcome="outcome",
            reasoning="reasoning",
        ),
    )

    verification_result, warnings, llm_calls = await verify_disputes_tyler_v1(
        stage_4_result=stage_4_result,
        bundle=bundle,
        stage_2_result=stage_2_result,
        trace_id="trace-1",
        max_disputes=1,
        max_budget=0.5,
    )

    assert verification_result.updated_claim_ledger[0].status == TylerClaimStatus.VERIFIED
    assert verification_result.disputes_investigated[0].resolution is ResolutionOutcome.CLAIM_SUPPORTED
    assert llm_calls == 1
    assert warnings == []


@pytest.mark.asyncio
async def test_verify_disputes_tyler_v1_prefers_persisted_tyler_stage_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 5 should not rebuild Tyler Stage 1/2 when they are already present."""
    monkeypatch.setattr("grounded_research.verify.get_depth_config", lambda: {"arbitration_max_rounds": 1})

    async def fail_decompose(*args, **kwargs):
        raise AssertionError("should not re-decompose")

    async def fake_collect(dispute_id, queries, bundle, trace_id):
        return [], [], []

    async def fake_arbitrate(**kwargs):
        from grounded_research.tyler_v1_models import ArbitrationAssessment, ClaimStatusUpdate

        return ArbitrationAssessment(
            dispute_id="D-1",
            new_evidence_summary="No decisive new evidence.",
            reasoning="Reasoning",
            resolution=ResolutionOutcome.EVIDENCE_INSUFFICIENT,
            updated_claim_statuses=[
                ClaimStatusUpdate(
                    claim_id="C-1",
                    new_status=TylerClaimStatus.UNRESOLVED,
                    confidence_in_resolution="medium",
                    remaining_uncertainty="Still open.",
                )
            ],
        )

    monkeypatch.setattr("grounded_research.decompose.decompose_question_tyler_v1", fail_decompose)
    monkeypatch.setattr("grounded_research.verify._collect_fresh_evidence_for_dispute", fake_collect)
    monkeypatch.setattr("grounded_research.verify.arbitrate_dispute_tyler_v1", fake_arbitrate)

    stage_1_result = DecompositionResult(
        core_question="Question",
        sub_questions=[
            SubQuestion(
                id="Q-1",
                question="Q1",
                type="empirical",
                research_priority="high",
                search_guidance="docs",
            ),
            SubQuestion(
                id="Q-2",
                question="Q2",
                type="interpretive",
                research_priority="medium",
                search_guidance="critiques",
            ),
        ],
        optimization_axes=["speed vs rigor"],
        research_plan=ResearchPlan(
            what_to_verify=["claim"],
            critical_source_types=["official docs"],
            falsification_targets=["contradiction"],
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
    stage_2_result = EvidencePackage(
        sub_question_evidence=[],
        total_queries_used=0,
        queries_per_sub_question={"Q-1": 0, "Q-2": 0},
        stage_summary=StageSummary(
            stage_name="Stage 2",
            goal="goal",
            key_findings=["k1", "k2", "k3"],
            decisions_made=["d1"],
            outcome="outcome",
            reasoning="reasoning",
        ),
    )
    stage_4_result = TylerClaimExtractionResult(
        claim_ledger=[
            ClaimLedgerEntry(
                id="C-1",
                statement="Claim",
                source_models=["A"],
                evidence_label=EvidenceLabel.EMPIRICALLY_OBSERVED,
                source_references=[],
                status=TylerClaimStatus.CONTESTED,
                supporting_models=["A"],
                contesting_models=["B"],
                related_assumptions=[],
            )
        ],
        assumption_set=[],
        dispute_queue=[
            DisputeQueueEntry(
                id="D-1",
                type=DisputeType.EMPIRICAL,
                description="Dispute",
                claims_involved=["C-1"],
                model_positions=[],
                decision_critical=True,
                decision_critical_rationale="critical",
                status=DisputeStatus.UNRESOLVED,
                resolution_routing="stage_5_evidence",
            )
        ],
        statistics={
            "total_claims": 1,
            "total_assumptions": 0,
            "total_disputes": 1,
            "disputes_by_type": {"empirical": 1},
            "decision_critical_disputes": 1,
            "claims_per_model": {"A": 1},
        },
        stage_summary={
            "stage_name": "Stage 4",
            "goal": "goal",
            "key_findings": ["k1", "k2", "k3"],
            "decisions_made": ["d1"],
            "outcome": "outcome",
            "reasoning": "reasoning",
        },
    )
    bundle = EvidenceBundle(
        question=ResearchQuestion(text="Question"),
        sources=[],
        evidence=[],
        gaps=[],
    )

    verification_result, warnings, llm_calls = await verify_disputes_tyler_v1(
        stage_4_result=stage_4_result,
        bundle=bundle,
        stage_1_result=stage_1_result,
        stage_2_result=stage_2_result,
        trace_id="trace-root",
        max_disputes=1,
        max_budget=1.0,
    )

    assert warnings == []
    assert llm_calls == 0
    assert verification_result.search_budget == {"D-1": 3}


@pytest.mark.asyncio
async def test_verify_disputes_tyler_v1_requires_canonical_stage2() -> None:
    """Stage 5 should fail loud when the canonical Tyler Stage 2 artifact is missing."""
    stage_4_result = TylerClaimExtractionResult(
        claim_ledger=[],
        assumption_set=[],
        dispute_queue=[],
        statistics={
            "total_claims": 0,
            "total_assumptions": 0,
            "total_disputes": 0,
            "disputes_by_type": {},
            "decision_critical_disputes": 0,
            "claims_per_model": {},
        },
        stage_summary={
            "stage_name": "Stage 4",
            "goal": "goal",
            "key_findings": ["k1", "k2", "k3"],
            "decisions_made": ["d1"],
            "outcome": "outcome",
            "reasoning": "reasoning",
        },
    )
    bundle = EvidenceBundle(
        question=ResearchQuestion(text="Question"),
        sources=[],
        evidence=[],
        gaps=[],
    )

    with pytest.raises(ValueError, match="Tyler Stage 5 requires a canonical Tyler Stage 2 EvidencePackage"):
        await verify_disputes_tyler_v1(
            stage_4_result=stage_4_result,
            bundle=bundle,
            trace_id="trace-root",
            max_disputes=1,
            max_budget=1.0,
        )
