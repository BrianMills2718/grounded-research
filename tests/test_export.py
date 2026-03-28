"""Tests for the canonical Tyler-native export path."""

from __future__ import annotations

from pathlib import Path

import pytest

from grounded_research.config import get_tyler_literal_parity_config
from grounded_research.export import (
    build_tyler_downstream_handoff,
    generate_tyler_synthesis_report,
    render_long_report,
    validate_tyler_grounding,
    write_outputs,
)
from grounded_research.models import (
    AnalystRun,
    EvidenceBundle,
    EvidenceItem,
    PipelineState,
    QuestionDecomposition,
    ResearchQuestion,
    SourceRecord,
    SubQuestion,
)
from grounded_research.tyler_v1_models import (
    ClaimExtractionResult as TylerClaimExtractionResult,
    ClaimLedgerEntry,
    ClaimStatus as TylerClaimStatus,
    ConfidenceAssessment,
    DecompositionResult,
    DisagreementMapEntry,
    DisputeType,
    EvidenceLabel,
    EvidencePackage,
    EvidenceTrailEntry,
    Finding,
    KeyAssumption,
    PreservedAlternative,
    ResearchPlan,
    Source,
    StageSummary,
    SubQuestion as TylerSubQuestion,
    SubQuestionEvidence,
    SynthesisReport,
    Tradeoff,
    VerificationResult,
)


def _stage_summary(stage_name: str) -> StageSummary:
    return StageSummary(
        stage_name=stage_name,
        goal="goal",
        key_findings=["k1", "k2", "k3"],
        decisions_made=["d1"],
        outcome="outcome",
        reasoning="reasoning",
    )


def _tyler_report() -> SynthesisReport:
    return SynthesisReport(
        executive_recommendation="Recommendation based on C-1.",
        conditions_of_validity=["If C-1 flips, reconsider."],
        decision_relevant_tradeoffs=[
            Tradeoff(
                if_optimize_for="stability",
                then_recommend="Choose the stable option.",
            )
        ],
        disagreement_map=[
            DisagreementMapEntry(
                dispute_id="D-1",
                type=DisputeType.INTERPRETIVE,
                summary="Interpretive split",
                resolution="Resolved conservatively.",
                action_taken="Stage 5 arbitration",
                chosen_interpretation="Conservative",
            )
        ],
        preserved_alternatives=[
            PreservedAlternative(
                alternative="Aggressive option",
                conditions_for_preference="Use if upside dominates downside.",
                supporting_claims=["C-2"],
            )
        ],
        key_assumptions=[
            KeyAssumption(
                assumption_id="A-1",
                statement="Assumption one.",
                if_wrong="Recommendation weakens.",
            )
        ],
        confidence_assessment=[
            ConfidenceAssessment(
                claim_summary="C-1",
                confidence="medium",
                basis="Evidence is decent.",
            )
        ],
        process_summary=[_stage_summary("Stage 6")],
        claim_ledger_excerpt=[
            {
                "claim_id": "C-1",
                "statement": "Primary claim",
                "final_status": "verified",
                "resolution_path": "Stage 5 supported it.",
            }
        ],
        evidence_trail=[
            EvidenceTrailEntry(
                source_id="S-1",
                url="https://example.com/source",
                quality_score=0.9,
                key_contribution="Supports C-1",
                conflicts_resolved=["D-1"],
            )
        ],
        evidence_gaps=["Need a larger sample."],
        reasoning="Reasoning",
        stage_summary=_stage_summary("Stage 6"),
    )


def _stage5_result_for_report() -> VerificationResult:
    return VerificationResult(
        disputes_investigated=[],
        additional_sources=[],
        updated_claim_ledger=[
            ClaimLedgerEntry(
                id="C-1",
                statement="Primary claim",
                source_models=["A"],
                evidence_label=EvidenceLabel.VENDOR_DOCUMENTED,
                source_references=["S-1"],
                status=TylerClaimStatus.VERIFIED,
                supporting_models=["A"],
                contesting_models=[],
                related_assumptions=[],
            )
        ],
        updated_dispute_queue=[],
        search_budget={},
        rounds_used=1,
        stage_summary=_stage_summary("Stage 5"),
    )


@pytest.mark.asyncio
async def test_render_long_report_uses_tyler_stage6_markdown_when_available() -> None:
    """Canonical long-report rendering should use Tyler Stage 6 directly."""
    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What should we do?"),
        tyler_stage_6_result=_tyler_report(),
    )

    markdown = await render_long_report(state, trace_id="trace-1", max_budget=0.5)

    assert "## Executive Recommendation" in markdown
    assert "C-1" in markdown


@pytest.mark.asyncio
async def test_render_long_report_requires_tyler_stage6() -> None:
    """The export layer should fail loud without the canonical Stage 6 artifact."""
    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What should we do?"),
    )

    with pytest.raises(ValueError, match="Canonical long-report rendering requires"):
        await render_long_report(state, trace_id="trace-1", max_budget=0.5)


@pytest.mark.asyncio
async def test_generate_tyler_synthesis_report_prefers_persisted_tyler_stage_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 6 should not rebuild Tyler Stage 1/2 when state already has them."""

    async def fail_decompose(*args, **kwargs):
        raise AssertionError("should not re-decompose")

    async def fake_acall_llm_structured(*args, **kwargs):
        response_model = kwargs["response_model"]
        return response_model(
            executive_recommendation="Recommendation.",
            conditions_of_validity=["Condition."],
            decision_relevant_tradeoffs=[{"if_optimize_for": "Speed", "then_recommend": "A"}],
            disagreement_map=[],
            preserved_alternatives=[
                {
                    "alternative": "Alternative",
                    "conditions_for_preference": "If cost dominates.",
                    "supporting_claims": ["C-1"],
                }
            ],
            key_assumptions=[],
            confidence_assessment=[{"claim_summary": "Summary", "confidence": "medium", "basis": "Basis"}],
            process_summary=[_stage_summary("Stage 6").model_dump(mode="json")],
            claim_ledger_excerpt=[{"claim_id": "C-1", "statement": "Claim", "final_status": "verified", "resolution_path": "Stage 5"}],
            evidence_trail=[{"source_id": "S-1", "url": "https://example.com", "quality_score": 0.9, "key_contribution": "Contribution"}],
            evidence_gaps=[],
            reasoning="Reasoning",
            stage_summary=_stage_summary("Stage 6").model_dump(mode="json"),
        ), {}

    monkeypatch.setattr("grounded_research.decompose.decompose_question_tyler_v1", fail_decompose)
    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr("llm_client.render_prompt", lambda *args, **kwargs: [{"role": "user", "content": "prompt"}])
    monkeypatch.setattr("grounded_research.export.get_model", lambda task: "test-model")
    monkeypatch.setattr("grounded_research.export.get_fallback_models", lambda task: None)

    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What is the evidence?"),
        evidence_bundle=EvidenceBundle(
            question=ResearchQuestion(text="What is the evidence?"),
            sources=[SourceRecord(id="S-1", url="https://example.com", title="Source", quality_tier="authoritative")],
            evidence=[EvidenceItem(id="E-1", source_id="S-1", content="Evidence", content_type="text")],
            gaps=[],
        ),
        tyler_stage_1_result=DecompositionResult(
            core_question="What is the evidence?",
            sub_questions=[
                TylerSubQuestion(id="Q-1", question="Q1", type="empirical", research_priority="high", search_guidance="docs"),
                TylerSubQuestion(id="Q-2", question="Q2", type="interpretive", research_priority="medium", search_guidance="critiques"),
            ],
            optimization_axes=["speed vs rigor"],
            research_plan=ResearchPlan(
                what_to_verify=["claim"],
                critical_source_types=["official docs"],
                falsification_targets=["contradiction"],
            ),
            stage_summary=_stage_summary("Stage 1"),
        ),
        tyler_stage_2_result=EvidencePackage(
            sub_question_evidence=[
                SubQuestionEvidence(
                    sub_question_id="Q-1",
                    sources=[
                        Source(
                            id="S-1",
                            url="https://example.com",
                            title="Source",
                            source_type="official_docs",
                            quality_score=0.9,
                            publication_date="2026-01-01",
                            retrieval_date="2026-03-27",
                            key_findings=[
                                Finding(
                                    finding="Finding",
                                    evidence_label=EvidenceLabel.VENDOR_DOCUMENTED,
                                    original_quote=None,
                                )
                            ],
                        )
                    ],
                    meets_sufficiency=False,
                    gap_description="Only one source",
                )
            ],
            total_queries_used=4,
            queries_per_sub_question={"Q-1": 4, "Q-2": 4},
            stage_summary=_stage_summary("Stage 2"),
        ),
        tyler_stage_4_result=TylerClaimExtractionResult(
            claim_ledger=[
                ClaimLedgerEntry(
                    id="C-1",
                    statement="Claim",
                    source_models=["A"],
                    evidence_label=EvidenceLabel.VENDOR_DOCUMENTED,
                    source_references=["S-1"],
                    status=TylerClaimStatus.VERIFIED,
                    supporting_models=["A"],
                    contesting_models=[],
                    related_assumptions=[],
                )
            ],
            assumption_set=[],
            dispute_queue=[],
            statistics={
                "total_claims": 1,
                "total_assumptions": 0,
                "total_disputes": 0,
                "disputes_by_type": {},
                "decision_critical_disputes": 0,
                "claims_per_model": {"A": 1},
            },
            stage_summary=_stage_summary("Stage 4"),
        ),
        tyler_stage_5_result=_stage5_result_for_report(),
    )

    result = await generate_tyler_synthesis_report(state, decomposition=None, trace_id="trace-root")

    assert result.executive_recommendation == "Recommendation."


@pytest.mark.asyncio
async def test_generate_tyler_synthesis_report_repairs_underfilled_decision_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tyler Stage 6 should retry when critical decision fields are empty."""
    calls = {"count": 0}

    async def fake_acall_llm_structured(*args, **kwargs):
        calls["count"] += 1
        response_model = kwargs["response_model"]
        payload = {
            "executive_recommendation": "Recommendation.",
            "conditions_of_validity": ["Condition."],
            "decision_relevant_tradeoffs": [{"if_optimize_for": "Speed", "then_recommend": "A"}],
            "disagreement_map": [],
            "preserved_alternatives": [{"alternative": "Alternative", "conditions_for_preference": "If cost dominates.", "supporting_claims": ["C-1"]}],
            "key_assumptions": [],
            "confidence_assessment": [{"claim_summary": "Summary", "confidence": "medium", "basis": "Basis"}],
            "process_summary": [_stage_summary("Stage 6").model_dump(mode="json")],
            "claim_ledger_excerpt": [{"claim_id": "C-1", "statement": "Claim", "final_status": "verified", "resolution_path": "Stage 5"}],
            "evidence_trail": [{"source_id": "S-1", "url": "https://example.com", "quality_score": 0.9, "key_contribution": "Contribution"}],
            "evidence_gaps": [],
            "reasoning": "Reasoning",
            "stage_summary": _stage_summary("Stage 6").model_dump(mode="json"),
        }
        if calls["count"] == 1:
            payload["decision_relevant_tradeoffs"] = []
            payload["preserved_alternatives"] = []
        return response_model(**payload), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr("llm_client.render_prompt", lambda *args, **kwargs: [{"role": "user", "content": "prompt"}])
    monkeypatch.setattr("grounded_research.export.get_model", lambda task: "test-model")
    monkeypatch.setattr("grounded_research.export.get_fallback_models", lambda task: None)

    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What is the evidence?"),
        evidence_bundle=EvidenceBundle(
            question=ResearchQuestion(text="What is the evidence?"),
            sources=[SourceRecord(id="S-1", url="https://example.com", title="Source", quality_tier="authoritative")],
            evidence=[EvidenceItem(id="E-1", source_id="S-1", content="Evidence", content_type="text")],
            gaps=[],
        ),
        tyler_stage_1_result=DecompositionResult(
            core_question="What is the evidence?",
            sub_questions=[
                TylerSubQuestion(id="Q-1", question="Q1", type="empirical", research_priority="high", search_guidance="docs"),
                TylerSubQuestion(id="Q-2", question="Q2", type="interpretive", research_priority="medium", search_guidance="critiques"),
            ],
            optimization_axes=["speed vs rigor"],
            research_plan=ResearchPlan(
                what_to_verify=["claim"],
                critical_source_types=["official docs"],
                falsification_targets=["contradiction"],
            ),
            stage_summary=_stage_summary("Stage 1"),
        ),
        tyler_stage_2_result=EvidencePackage(
            sub_question_evidence=[],
            total_queries_used=0,
            queries_per_sub_question={},
            stage_summary=_stage_summary("Stage 2"),
        ),
        tyler_stage_4_result=TylerClaimExtractionResult(
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
            stage_summary=_stage_summary("Stage 4"),
        ),
        tyler_stage_5_result=VerificationResult(
            disputes_investigated=[],
            additional_sources=[],
            updated_claim_ledger=[],
            updated_dispute_queue=[],
            search_budget={},
            rounds_used=1,
            stage_summary=_stage_summary("Stage 5"),
        ),
    )

    result = await generate_tyler_synthesis_report(state, decomposition=None, trace_id="trace-root")

    assert calls["count"] == 2
    assert len(result.decision_relevant_tradeoffs) >= int(get_tyler_literal_parity_config()["stage6_min_tradeoffs"])
    assert len(result.preserved_alternatives) >= int(
        get_tyler_literal_parity_config()["stage6_min_preserved_alternatives"]
    )


@pytest.mark.asyncio
async def test_generate_tyler_synthesis_report_redecomposes_from_question_when_missing_stage1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 6 should regenerate Tyler Stage 1 from the question when missing."""
    calls: dict[str, int] = {"decompose": 0}

    async def fake_decompose_question_tyler_v1(question: str, trace_id: str, max_budget: float = 0.5):
        calls["decompose"] += 1
        assert question == "What is the evidence?"
        return DecompositionResult(
            core_question=question,
            sub_questions=[
                TylerSubQuestion(id="Q-1", question="Q1", type="empirical", research_priority="high", search_guidance="docs"),
                TylerSubQuestion(id="Q-2", question="Q2", type="interpretive", research_priority="medium", search_guidance="critiques"),
            ],
            optimization_axes=["speed vs rigor"],
            research_plan=ResearchPlan(
                what_to_verify=["claim"],
                critical_source_types=["official docs"],
                falsification_targets=["contradiction"],
            ),
            stage_summary=_stage_summary("Stage 1"),
        )

    async def fake_acall_llm_structured(*args, **kwargs):
        response_model = kwargs["response_model"]
        return response_model(
            executive_recommendation="Recommendation.",
            conditions_of_validity=["Condition."],
            decision_relevant_tradeoffs=[{"if_optimize_for": "Speed", "then_recommend": "A"}],
            disagreement_map=[],
            preserved_alternatives=[{"alternative": "Alternative", "conditions_for_preference": "If cost dominates.", "supporting_claims": ["C-1"]}],
            key_assumptions=[],
            confidence_assessment=[{"claim_summary": "Summary", "confidence": "medium", "basis": "Basis"}],
            process_summary=[_stage_summary("Stage 6").model_dump(mode="json")],
            claim_ledger_excerpt=[{"claim_id": "C-1", "statement": "Claim", "final_status": "verified", "resolution_path": "Stage 5"}],
            evidence_trail=[{"source_id": "S-1", "url": "https://example.com", "quality_score": 0.9, "key_contribution": "Contribution"}],
            evidence_gaps=[],
            reasoning="Reasoning",
            stage_summary=_stage_summary("Stage 6").model_dump(mode="json"),
        ), {}

    monkeypatch.setattr("grounded_research.decompose.decompose_question_tyler_v1", fake_decompose_question_tyler_v1)
    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr("llm_client.render_prompt", lambda *args, **kwargs: [{"role": "user", "content": "prompt"}])
    monkeypatch.setattr("grounded_research.export.get_model", lambda task: "test-model")
    monkeypatch.setattr("grounded_research.export.get_fallback_models", lambda task: None)

    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What is the evidence?"),
        evidence_bundle=EvidenceBundle(
            question=ResearchQuestion(text="What is the evidence?"),
            sources=[SourceRecord(id="S-1", url="https://example.com", title="Source", quality_tier="authoritative")],
            evidence=[EvidenceItem(id="E-1", source_id="S-1", content="Evidence", content_type="text")],
            gaps=[],
        ),
        tyler_stage_2_result=EvidencePackage(
            sub_question_evidence=[],
            total_queries_used=0,
            queries_per_sub_question={},
            stage_summary=_stage_summary("Stage 2"),
        ),
        tyler_stage_4_result=TylerClaimExtractionResult(
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
            stage_summary=_stage_summary("Stage 4"),
        ),
        tyler_stage_5_result=VerificationResult(
            disputes_investigated=[],
            additional_sources=[],
            updated_claim_ledger=[],
            updated_dispute_queue=[],
            search_budget={},
            rounds_used=1,
            stage_summary=_stage_summary("Stage 5"),
        ),
    )

    decomposition = QuestionDecomposition(
        core_question="Legacy projection",
        sub_questions=[
            SubQuestion(text="Legacy Q1", type="factual", falsification_target="counter"),
            SubQuestion(text="Legacy Q2", type="evaluative", falsification_target="counter"),
        ],
        optimization_axes=["legacy axis"],
        research_plan="legacy plan",
        ambiguous_terms=[],
    )

    result = await generate_tyler_synthesis_report(
        state,
        decomposition=decomposition,
        trace_id="trace-root",
    )

    assert calls["decompose"] == 1
    assert result.executive_recommendation == "Recommendation."


@pytest.mark.asyncio
async def test_generate_tyler_synthesis_report_requires_canonical_stage2() -> None:
    """Stage 6 should fail loud when the canonical Tyler Stage 2 artifact is missing."""
    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What is the evidence?"),
        evidence_bundle=EvidenceBundle(
            question=ResearchQuestion(text="What is the evidence?"),
            sources=[],
            evidence=[],
            gaps=[],
        ),
        tyler_stage_1_result=DecompositionResult(
            core_question="What is the evidence?",
            sub_questions=[
                TylerSubQuestion(id="Q-1", question="Q1", type="empirical", research_priority="high", search_guidance="docs"),
                TylerSubQuestion(id="Q-2", question="Q2", type="interpretive", research_priority="medium", search_guidance="critiques"),
            ],
            optimization_axes=["speed vs rigor"],
            research_plan=ResearchPlan(
                what_to_verify=["claim"],
                critical_source_types=["official docs"],
                falsification_targets=["contradiction"],
            ),
            stage_summary=_stage_summary("Stage 1"),
        ),
        tyler_stage_4_result=TylerClaimExtractionResult(
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
            stage_summary=_stage_summary("Stage 4"),
        ),
        tyler_stage_5_result=VerificationResult(
            disputes_investigated=[],
            additional_sources=[],
            updated_claim_ledger=[],
            updated_dispute_queue=[],
            search_budget={},
            rounds_used=1,
            stage_summary=_stage_summary("Stage 5"),
        ),
    )

    with pytest.raises(ValueError, match="Tyler Stage 6 requires a canonical Tyler Stage 2 EvidencePackage"):
        await generate_tyler_synthesis_report(
            state,
            decomposition=None,
            trace_id="trace-root",
        )


def test_successful_analyst_run_requires_quality_minimums() -> None:
    """Successful analyst outputs must meet the configured structural floor."""
    with pytest.raises(ValueError):
        AnalystRun(
            analyst_label="Alpha",
            model="openrouter/openai/gpt-5-nano",
            frame="verification_first",
            summary="A successful run without counterarguments should fail validation.",
        )


def test_failed_analyst_run_allows_empty_counterarguments() -> None:
    """Failed analyst trace artifacts should not require semantic counterarguments."""
    result = AnalystRun(
        analyst_label="Alpha",
        model="openrouter/openai/gpt-5-nano",
        frame="verification_first",
        error="rate limit",
    )

    assert result.counterarguments == []
    assert not result.succeeded


def test_validate_tyler_grounding_checks_stage5_claims_and_sources() -> None:
    """Tyler-native grounding should validate against Stage 5 and known sources."""
    report = _tyler_report()
    verification_result = _stage5_result_for_report()
    bundle = EvidenceBundle(
        question=ResearchQuestion(text="What is the evidence?"),
        sources=[
            SourceRecord(
                id="S-1",
                url="https://example.com/source",
                title="Source",
                quality_tier="authoritative",
            )
        ],
        evidence=[EvidenceItem(id="E-1", source_id="S-1", content="Evidence", content_type="text")],
        gaps=[],
    )

    assert validate_tyler_grounding(
        report,
        verification_result=verification_result,
        bundle=bundle,
    ) == []


def test_write_outputs_prefers_tyler_summary_when_present(tmp_path: Path) -> None:
    """Summary output should render from Tyler Stage 6 when the canonical artifact exists."""
    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What is the evidence?"),
        evidence_bundle=EvidenceBundle(
            question=ResearchQuestion(text="What is the evidence?"),
            sources=[
                SourceRecord(
                    id="S-1",
                    url="https://example.com/source",
                    title="Source",
                    quality_tier="authoritative",
                )
            ],
            evidence=[EvidenceItem(id="E-1", source_id="S-1", content="Evidence", content_type="text")],
            gaps=[],
        ),
        tyler_stage_6_result=_tyler_report(),
    )

    paths = write_outputs(state, tmp_path, long_report_md="# Long report")

    summary = paths["summary"].read_text()
    assert "## Executive Recommendation" in summary
    assert "Recommendation based on C-1." in summary
    assert "report" in paths


def test_build_tyler_downstream_handoff_prefers_canonical_stage_artifacts() -> None:
    """Canonical handoff should preserve Tyler Stage 2/5/6 directly."""
    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What is the evidence?"),
        tyler_stage_2_result=EvidencePackage(
            sub_question_evidence=[],
            total_queries_used=0,
            queries_per_sub_question={},
            stage_summary=_stage_summary("Stage 2"),
        ),
        tyler_stage_5_result=_stage5_result_for_report(),
        tyler_stage_6_result=_tyler_report(),
    )

    handoff = build_tyler_downstream_handoff(state)

    assert handoff.question.text == "What is the evidence?"
    assert handoff.stage_5_verification_result.updated_claim_ledger[0].id == "C-1"
    assert handoff.stage_6_synthesis_report.claim_ledger_excerpt[0].claim_id == "C-1"
