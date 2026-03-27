"""Tests for Tyler Stage 4 normalization and ledger projection."""

from __future__ import annotations

from datetime import datetime, timezone

from grounded_research.models import (
    AnalystRun,
    Counterargument,
    EvidenceBundle,
    EvidenceItem,
    QuestionDecomposition,
    RawClaim,
    Recommendation,
    ResearchQuestion,
    SourceRecord,
    SubQuestion,
)
from grounded_research.tyler_v1_adapters import (
    build_tyler_alias_mapping,
    current_decomposition_to_tyler,
    normalize_tyler_claim_extraction_result,
    tyler_stage4_to_current_ledger,
)
from grounded_research.tyler_v1_models import ClaimExtractionResult, ClaimStatus, EvidenceLabel


def _bundle() -> EvidenceBundle:
    retrieved_at = datetime(2026, 3, 27, tzinfo=timezone.utc)
    return EvidenceBundle(
        question=ResearchQuestion(text="Should cities adopt UBI pilots?"),
        sources=[
            SourceRecord(
                id="S-1",
                url="https://example.com/1",
                title="Pilot one",
                source_type="academic",
                quality_tier="authoritative",
                retrieved_at=retrieved_at,
            ),
            SourceRecord(
                id="S-2",
                url="https://example.com/2",
                title="Pilot two",
                source_type="news",
                quality_tier="reliable",
                retrieved_at=retrieved_at,
            ),
        ],
        evidence=[
            EvidenceItem(id="E-1", source_id="S-1", content="Employment stayed flat."),
            EvidenceItem(id="E-2", source_id="S-2", content="Households reported less stress."),
        ],
    )


def _analyst_runs() -> list[AnalystRun]:
    return [
        AnalystRun(
            analyst_label="Alpha",
            frame="verification_first",
            model="m1",
            claims=[RawClaim(id="RC-a1", statement="Employment stayed flat in the pilot.", evidence_ids=["E-1"])],
            assumptions=[],
            recommendations=[Recommendation(statement="Adopt a limited pilot.", supporting_claim_ids=["RC-a1"])],
            counterarguments=[Counterargument(target="pilot", argument="The evidence base is narrow.", evidence_ids=["E-2"])],
            summary="Alpha summary",
        ),
        AnalystRun(
            analyst_label="Beta",
            frame="structured_decomposition",
            model="m2",
            claims=[RawClaim(id="RC-b1", statement="UBI reduced financial stress for recipients.", evidence_ids=["E-2"])],
            assumptions=[],
            recommendations=[Recommendation(statement="Adopt a limited pilot.", supporting_claim_ids=["RC-b1"])],
            counterarguments=[Counterargument(target="pilot", argument="Labor effects remain uncertain.", evidence_ids=["E-1"])],
            summary="Beta summary",
        ),
    ]


def test_current_decomposition_to_tyler_preserves_core_structure() -> None:
    current = QuestionDecomposition(
        core_question="Should cities adopt UBI pilots?",
        sub_questions=[
            SubQuestion(id="SQ-1", text="What happened in prior pilots?", type="factual", falsification_target="Prior pilots caused severe harm."),
            SubQuestion(id="SQ-2", text="How should policymakers interpret mixed evidence?", type="evaluative", falsification_target="Interpretive consensus rejects pilots."),
        ],
        optimization_axes=["risk vs upside"],
        research_plan="official docs; evaluations; contradictory evidence",
    )
    tyler = current_decomposition_to_tyler(current, original_query=current.core_question)
    assert tyler.core_question == current.core_question
    assert [sq.id for sq in tyler.sub_questions] == ["Q-1", "Q-2"]
    assert tyler.sub_questions[0].type == "empirical"


def test_normalize_tyler_claim_extraction_result_rewrites_ids_and_routes() -> None:
    raw = ClaimExtractionResult.model_validate(
        {
            "claim_ledger": [
                {
                    "id": "bad-claim",
                    "statement": "Pilot employment effects were neutral.",
                    "source_models": ["A"],
                    "evidence_label": "empirically_observed",
                    "source_references": ["S-1", "S-missing"],
                    "status": "verified",
                    "supporting_models": [],
                    "contesting_models": [],
                    "related_assumptions": ["assumption-x"],
                }
            ],
            "assumption_set": [
                {
                    "id": "assumption-x",
                    "statement": "The pilot population is representative.",
                    "source_models": ["A", "ghost"],
                    "dependent_claims": ["bad-claim"],
                    "if_wrong_impact": "The claim weakens.",
                    "shared_across_models": False,
                }
            ],
            "dispute_queue": [
                {
                    "id": "weird-dispute",
                    "type": "empirical",
                    "description": "Whether the pilot changed employment.",
                    "claims_involved": ["bad-claim"],
                    "model_positions": [],
                    "decision_critical": True,
                    "decision_critical_rationale": "",
                    "status": "resolved",
                    "resolution_routing": "wrong",
                }
            ],
            "statistics": {
                "total_claims": 999,
                "total_assumptions": 999,
                "total_disputes": 999,
                "disputes_by_type": {"empirical": 999},
                "decision_critical_disputes": 999,
                "claims_per_model": {"A": 999},
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
    )

    normalized = normalize_tyler_claim_extraction_result(
        raw,
        valid_source_ids={"S-1", "S-2"},
        allowed_model_aliases={"A", "B", "C"},
    )

    assert normalized.claim_ledger[0].id == "C-1"
    assert normalized.assumption_set[0].id == "A-1"
    assert normalized.dispute_queue[0].id == "D-1"
    assert normalized.claim_ledger[0].source_references == ["S-1"]
    assert normalized.claim_ledger[0].status is ClaimStatus.CONTESTED
    assert normalized.dispute_queue[0].resolution_routing == "stage_5_evidence"
    assert normalized.statistics.total_claims == 1
    assert normalized.statistics.decision_critical_disputes == 1


def test_tyler_stage4_to_current_ledger_preserves_claim_and_dispute_integrity() -> None:
    bundle = _bundle()
    analyst_runs = _analyst_runs()
    alias_mapping = build_tyler_alias_mapping(analyst_runs)
    result = ClaimExtractionResult.model_validate(
        {
            "claim_ledger": [
                {
                    "id": "C-1",
                    "statement": "Employment stayed flat in the pilot.",
                    "source_models": ["A"],
                    "evidence_label": EvidenceLabel.EMPIRICALLY_OBSERVED.value,
                    "source_references": ["S-1"],
                    "status": "supported",
                    "supporting_models": ["A"],
                    "contesting_models": ["B"],
                    "related_assumptions": [],
                },
                {
                    "id": "C-2",
                    "statement": "Recipients reported lower stress.",
                    "source_models": ["B"],
                    "evidence_label": EvidenceLabel.EMPIRICALLY_OBSERVED.value,
                    "source_references": ["S-2"],
                    "status": "supported",
                    "supporting_models": ["B"],
                    "contesting_models": ["A"],
                    "related_assumptions": [],
                },
            ],
            "assumption_set": [],
            "dispute_queue": [
                {
                    "id": "D-1",
                    "type": "interpretive",
                    "description": "How much these findings support pilots.",
                    "claims_involved": ["C-1", "C-2"],
                    "model_positions": [
                        {"model_alias": "A", "position": "Neutral labor effects matter most."},
                        {"model_alias": "B", "position": "Stress reduction matters most."},
                    ],
                    "decision_critical": True,
                    "decision_critical_rationale": "Could change the recommendation.",
                    "status": "unresolved",
                    "resolution_routing": "stage_5_arbitration",
                }
            ],
            "statistics": {
                "total_claims": 2,
                "total_assumptions": 0,
                "total_disputes": 1,
                "disputes_by_type": {"interpretive": 1},
                "decision_critical_disputes": 1,
                "claims_per_model": {"A": 1, "B": 1},
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
    )

    ledger = tyler_stage4_to_current_ledger(
        result,
        analyst_runs=analyst_runs,
        bundle=bundle,
        alias_mapping=alias_mapping,
    )

    assert [claim.id for claim in ledger.claims] == ["C-1", "C-2"]
    assert ledger.claims[0].source_raw_claim_ids
    assert ledger.claims[0].evidence_ids == ["E-1"]
    assert ledger.disputes[0].id == "D-1"
    assert ledger.disputes[0].claim_ids == ["C-1", "C-2"]
    assert ledger.disputes[0].route == "arbitrate"
