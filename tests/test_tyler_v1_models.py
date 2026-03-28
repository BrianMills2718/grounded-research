"""Tests for the literal Tyler V1 schema contract module."""

from __future__ import annotations

from grounded_research.tyler_v1_models import (
    AnalysisObject,
    ArbitrationAssessment,
    ClaimExtractionResult,
    ClaimLedgerEntry,
    ClaimStatus,
    ClaimStatusUpdate,
    ConfidenceAssessment,
    ConfidenceLevel,
    CounterArgument,
    DecompositionResult,
    DisagreementMapEntry,
    DisputeQueueEntry,
    DisputeStatus,
    DisputeType,
    EvidenceLabel,
    EvidencePackage,
    EvidenceTrailEntry,
    ExtractionStatistics,
    Finding,
    PipelineState,
    PreservedAlternative,
    ResearchPlan,
    ResolutionOutcome,
    Source,
    StageSummary,
    SubQuestion,
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


def test_tyler_v1_enum_values_match_literal_spec() -> None:
    assert [e.value for e in EvidenceLabel] == [
        "vendor_documented",
        "empirically_observed",
        "model_self_characterization",
        "speculative_inference",
    ]
    assert [e.value for e in DisputeType] == [
        "empirical",
        "interpretive",
        "preference_weighted",
        "spec_ambiguity",
        "other",
    ]
    assert [e.value for e in ClaimStatus] == [
        "initial",
        "supported",
        "contested",
        "contradicted",
        "insufficient_evidence",
        "verified",
        "refuted",
        "unresolved",
    ]
    assert [e.value for e in DisputeStatus] == [
        "unresolved",
        "resolved",
        "deferred_to_user",
        "logged_only",
    ]
    assert [e.value for e in ConfidenceLevel] == ["high", "medium", "low"]
    assert [e.value for e in ResolutionOutcome] == [
        "claim_supported",
        "claim_refuted",
        "evidence_insufficient",
        "interpretation_revised",
    ]


def test_decomposition_result_parses_minimal_valid_fixture() -> None:
    result = DecompositionResult.model_validate(
        {
            "core_question": "What matters most?",
            "sub_questions": [
                {
                    "id": "Q-1",
                    "question": "What does the evidence say?",
                    "type": "empirical",
                    "research_priority": "high",
                    "search_guidance": "official docs and benchmarks",
                },
                {
                    "id": "Q-2",
                    "question": "How should the evidence be interpreted?",
                    "type": "interpretive",
                    "research_priority": "medium",
                    "search_guidance": "reviews and practitioner reports",
                },
            ],
            "optimization_axes": ["cost vs quality"],
            "research_plan": {
                "what_to_verify": ["throughput"],
                "critical_source_types": ["official docs"],
                "falsification_targets": ["benchmark contradictions"],
            },
            "stage_summary": _stage_summary("Stage 1: Intake & Decomposition").model_dump(),
        }
    )
    assert result.sub_questions[0].id == "Q-1"
    assert result.research_plan.falsification_targets == ["benchmark contradictions"]


def test_stage_3_and_stage_4_contracts_parse_representative_payloads() -> None:
    analysis = AnalysisObject.model_validate(
        {
            "model_alias": "A",
            "reasoning_frame": "step_back_abstraction",
            "recommendation": "Use approach A.",
            "claims": [
                {
                    "id": "C-1",
                    "statement": "A benchmark found 10% improvement.",
                    "evidence_label": "empirically_observed",
                    "source_references": ["S-1"],
                    "confidence": "high",
                }
            ],
            "assumptions": [
                {
                    "id": "A-1",
                    "statement": "Traffic profile is representative.",
                    "depends_on_claims": ["C-1"],
                    "if_wrong_impact": "Recommendation weakens.",
                }
            ],
            "evidence_used": ["S-1"],
            "counter_argument": {
                "argument": "Benchmark may not generalize.",
                "strongest_evidence_against": "Production load differs.",
                "counter_confidence": "medium",
            },
            "falsification_conditions": ["Production benchmark reverses result"],
            "reasoning": "Reasoning chain",
            "stage_summary": _stage_summary("Stage 3: Independent Candidate Generation").model_dump(),
        }
    )
    assert analysis.claims[0].evidence_label is EvidenceLabel.EMPIRICALLY_OBSERVED

    extraction = ClaimExtractionResult.model_validate(
        {
            "claim_ledger": [
                {
                    "id": "C-10",
                    "statement": "Canonical claim",
                    "source_models": ["A", "B"],
                    "evidence_label": "empirically_observed",
                    "source_references": ["S-1"],
                    "status": "supported",
                    "supporting_models": ["A", "B"],
                    "contesting_models": [],
                    "related_assumptions": ["A-10"],
                }
            ],
            "assumption_set": [
                {
                    "id": "A-10",
                    "statement": "Shared assumption",
                    "source_models": ["A", "B"],
                    "dependent_claims": ["C-10"],
                    "if_wrong_impact": "Claim weakens",
                    "shared_across_models": True,
                }
            ],
            "dispute_queue": [
                {
                    "id": "D-1",
                    "type": "empirical",
                    "description": "Empirical disagreement",
                    "claims_involved": ["C-10"],
                    "model_positions": [{"model_alias": "A", "position": "supports"}],
                    "decision_critical": True,
                    "decision_critical_rationale": "Changes recommendation",
                    "status": "unresolved",
                    "resolution_routing": "stage_5_evidence",
                }
            ],
            "statistics": {
                "total_claims": 1,
                "total_assumptions": 1,
                "total_disputes": 1,
                "disputes_by_type": {"empirical": 1},
                "decision_critical_disputes": 1,
                "claims_per_model": {"A": 1},
            },
            "stage_summary": _stage_summary("Stage 4: Claim Extraction & Dispute Localization").model_dump(),
        }
    )
    assert extraction.dispute_queue[0].type is DisputeType.EMPIRICAL


def test_stage_5_and_stage_6_contracts_parse_representative_payloads() -> None:
    verification = VerificationResult.model_validate(
        {
            "disputes_investigated": [
                {
                    "dispute_id": "D-1",
                    "new_evidence_summary": "Fresh search favored one side.",
                    "reasoning": "Reasoning",
                    "resolution": "claim_supported",
                    "updated_claim_statuses": [
                        {
                            "claim_id": "C-10",
                            "new_status": "verified",
                            "confidence_in_resolution": "high",
                            "remaining_uncertainty": None,
                        }
                    ],
                }
            ],
            "additional_sources": [
                {
                    "source_id": "S-99",
                    "url": "https://example.com",
                    "title": "Fresh source",
                    "quality_score": 0.9,
                    "key_findings": ["finding"],
                    "retrieved_for_dispute": "D-1",
                }
            ],
            "updated_claim_ledger": [
                {
                    "id": "C-10",
                    "statement": "Canonical claim",
                    "source_models": ["A"],
                    "evidence_label": "empirically_observed",
                    "source_references": ["S-1", "S-99"],
                    "status": "verified",
                    "supporting_models": ["A"],
                    "contesting_models": [],
                    "related_assumptions": [],
                }
            ],
            "updated_dispute_queue": [
                {
                    "id": "D-1",
                    "type": "empirical",
                    "description": "Empirical disagreement",
                    "claims_involved": ["C-10"],
                    "model_positions": [{"model_alias": "A", "position": "supports"}],
                    "decision_critical": True,
                    "decision_critical_rationale": "Changes recommendation",
                    "status": "resolved",
                    "resolution_routing": "stage_5_evidence",
                }
            ],
            "search_budget": {"D-1": 2},
            "rounds_used": 1,
            "stage_summary": _stage_summary("Stage 5: Targeted Verification & Arbitration").model_dump(),
        }
    )
    assert verification.disputes_investigated[0].resolution is ResolutionOutcome.CLAIM_SUPPORTED

    report = SynthesisReport.model_validate(
        {
            "executive_recommendation": "Recommend option A based on claim C-10.",
            "conditions_of_validity": ["If context remains stable"],
            "decision_relevant_tradeoffs": [{"if_optimize_for": "cost", "then_recommend": "A"}],
            "disagreement_map": [
                {
                    "dispute_id": "D-1",
                    "type": "interpretive",
                    "summary": "Interpretive split",
                    "resolution": "resolved in favor of A",
                    "action_taken": "stage_5_arbitration",
                    "chosen_interpretation": "Interpretation A",
                }
            ],
            "preserved_alternatives": [
                {
                    "alternative": "Option B",
                    "conditions_for_preference": "Choose when speed dominates",
                    "supporting_claims": ["C-11"],
                }
            ],
            "key_assumptions": [
                {
                    "assumption_id": "A-10",
                    "statement": "Representative demand",
                    "if_wrong": "Recommendation weakens",
                }
            ],
            "confidence_assessment": [
                {
                    "claim_summary": "The main claim",
                    "confidence": "medium",
                    "basis": "Backed by two strong studies",
                }
            ],
            "process_summary": [
                _stage_summary("Stage 1").model_dump(),
                _stage_summary("Stage 2").model_dump(),
            ],
            "claim_ledger_excerpt": [
                {
                    "claim_id": "C-10",
                    "statement": "Canonical claim",
                    "final_status": "verified",
                    "resolution_path": "Stage 5 evidence",
                }
            ],
            "evidence_trail": [
                {
                    "source_id": "S-1",
                    "url": "https://example.com",
                    "quality_score": 0.9,
                    "key_contribution": "Primary evidence",
                    "conflicts_resolved": ["D-1"],
                }
            ],
            "evidence_gaps": ["No long-run macro evidence"],
            "reasoning": "Synthesis reasoning",
            "stage_summary": _stage_summary("Stage 6: Synthesis & Report").model_dump(),
        }
    )
    assert report.disagreement_map[0].type is DisputeType.INTERPRETIVE
    assert report.confidence_assessment[0].confidence is ConfidenceLevel.MEDIUM


def test_pipeline_state_accepts_tyler_stage_results() -> None:
    stage_1 = DecompositionResult.model_validate(
        {
            "core_question": "Question",
            "sub_questions": [
                {
                    "id": "Q-1",
                    "question": "Q1",
                    "type": "empirical",
                    "research_priority": "high",
                    "search_guidance": "official docs",
                },
                {
                    "id": "Q-2",
                    "question": "Q2",
                    "type": "interpretive",
                    "research_priority": "medium",
                    "search_guidance": "benchmarks",
                },
            ],
            "optimization_axes": ["cost vs quality"],
            "research_plan": {
                "what_to_verify": ["claim"],
                "critical_source_types": ["official docs"],
                "falsification_targets": ["contradiction"],
            },
            "stage_summary": _stage_summary("Stage 1").model_dump(),
        }
    )
    stage_2 = EvidencePackage.model_validate(
        {
            "sub_question_evidence": [
                {
                    "sub_question_id": "Q-1",
                    "sources": [
                        {
                            "id": "S-1",
                            "url": "https://example.com",
                            "title": "Source",
                            "source_type": "official_docs",
                            "quality_score": 0.9,
                            "publication_date": "2026-03-27",
                            "retrieval_date": "2026-03-27",
                            "key_findings": [
                                {
                                    "finding": "Measured result",
                                    "evidence_label": "empirically_observed",
                                    "original_quote": None,
                                }
                            ],
                        }
                    ],
                    "meets_sufficiency": True,
                    "gap_description": None,
                }
            ],
            "total_queries_used": 4,
            "queries_per_sub_question": {"Q-1": 2},
            "stage_summary": _stage_summary("Stage 2").model_dump(),
        }
    )
    state = PipelineState.model_validate(
        {
            "query_id": "query-1",
            "original_query": "What should we do?",
            "started_at": "2026-03-27T00:00:00Z",
            "current_stage": 2,
            "stage_1_result": stage_1.model_dump(),
            "stage_2_result": stage_2.model_dump(),
            "errors": [],
        }
    )
    assert state.stage_1_result is not None
    assert state.stage_2_result is not None
