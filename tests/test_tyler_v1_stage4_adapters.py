"""Tests for the remaining Tyler Stage 1 and Stage 4 adapter helpers."""

from __future__ import annotations

from grounded_research.models import QuestionDecomposition, SubQuestion
from grounded_research.tyler_v1_adapters import (
    current_decomposition_to_tyler,
    normalize_tyler_claim_extraction_result,
)
from grounded_research.tyler_v1_models import ClaimExtractionResult, ClaimStatus


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
