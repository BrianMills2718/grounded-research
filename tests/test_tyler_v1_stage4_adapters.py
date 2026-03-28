"""Tests for the remaining Tyler Stage 4 normalization helpers."""

from __future__ import annotations

from grounded_research.tyler_v1_adapters import normalize_tyler_claim_extraction_result
from grounded_research.tyler_v1_models import ClaimExtractionResult, ClaimStatus


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
