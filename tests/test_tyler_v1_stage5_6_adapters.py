"""Tests for Tyler Stage 5/6 projection helpers."""

from __future__ import annotations

from grounded_research.models import Claim, ClaimLedger, Dispute
from grounded_research.tyler_v1_adapters import (
    render_tyler_synthesis_markdown,
    tyler_assessment_to_current_arbitration,
)
from grounded_research.tyler_v1_models import (
    AdditionalSource,
    ArbitrationAssessment,
    ClaimLedgerEntry,
    ClaimStatus,
    ClaimStatusUpdate,
    ConfidenceAssessment,
    DisagreementMapEntry,
    DisputeQueueEntry,
    DisputeStatus,
    DisputeType,
    EvidenceLabel,
    EvidenceTrailEntry,
    KeyAssumption,
    PreservedAlternative,
    ResolutionOutcome,
    StageSummary,
    SynthesisReport,
    Tradeoff,
    VerificationResult,
)


def _stage_summary(name: str) -> StageSummary:
    return StageSummary(
        stage_name=name,
        goal="goal",
        key_findings=["k1", "k2", "k3"],
        decisions_made=["d1"],
        outcome="outcome",
        reasoning="reasoning",
    )


def test_tyler_assessment_to_current_arbitration_maps_resolution_and_sources() -> None:
    assessment = ArbitrationAssessment(
        dispute_id="D-1",
        new_evidence_summary="Fresh evidence favored one side.",
        reasoning="Reasoning",
        resolution=ResolutionOutcome.CLAIM_SUPPORTED,
        updated_claim_statuses=[
            ClaimStatusUpdate(
                claim_id="C-1",
                new_status=ClaimStatus.VERIFIED,
                confidence_in_resolution="high",
                remaining_uncertainty=None,
            )
        ],
    )
    additional_sources = [
        AdditionalSource(
            source_id="S-99",
            url="https://example.com/fresh",
            title="Fresh source",
            quality_score=0.8,
            key_findings=["Fresh finding"],
            retrieved_for_dispute="D-1",
        )
    ]

    result = tyler_assessment_to_current_arbitration(assessment, additional_sources)

    assert result.dispute_id == "D-1"
    assert result.verdict == "supported"
    assert result.new_evidence_ids == ["S-99"]
    assert result.claim_updates[0].new_status == "supported"


def test_tyler_synthesis_markdown_render() -> None:
    report = SynthesisReport(
        executive_recommendation="Recommendation based on C-1.",
        conditions_of_validity=["If C-1 stops holding, reconsider."],
        decision_relevant_tradeoffs=[Tradeoff(if_optimize_for="stability", then_recommend="Choose the conservative path.")],
        disagreement_map=[
            DisagreementMapEntry(
                dispute_id="D-1",
                type=DisputeType.INTERPRETIVE,
                summary="Interpretive split",
                resolution="Resolved toward the conservative interpretation.",
                action_taken="Stage 5 arbitration",
                chosen_interpretation="Conservative interpretation",
            )
        ],
        preserved_alternatives=[
            PreservedAlternative(
                alternative="Aggressive rollout",
                conditions_for_preference="Use if upside dominates downside.",
                supporting_claims=["C-2"],
            )
        ],
        key_assumptions=[KeyAssumption(assumption_id="A-1", statement="Adoption conditions remain stable.", if_wrong="Recommendation weakens.")],
        confidence_assessment=[ConfidenceAssessment(claim_summary="C-1 support", confidence="medium", basis="Evidence is decent but not perfect.")],
        process_summary=[_stage_summary("Stage 1")],
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
                key_contribution="Primary support for C-1",
                conflicts_resolved=["D-1"],
            )
        ],
        evidence_gaps=["Need a larger sample."],
        reasoning="Reasoning",
        stage_summary=_stage_summary("Stage 6"),
    )

    markdown = render_tyler_synthesis_markdown(report, original_query="What should we do?")

    assert "## Executive Recommendation" in markdown
    assert "C-1" in markdown
