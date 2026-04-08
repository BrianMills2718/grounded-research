"""Focused engine tests for Tyler remediation behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine import _select_stage6a_steering_disputes, run_pipeline
from grounded_research.models import EvidenceBundle, ResearchQuestion, SourceRecord
from grounded_research.tyler_v1_models import (
    ClaimExtractionResult,
    ClaimLedgerEntry,
    ClaimStatus,
    DecompositionResult,
    DisagreementMapEntry,
    DisputeQueueEntry,
    DisputeStatus,
    DisputeType,
    EvidenceLabel,
    EvidencePackage,
    EvidenceTrailEntry,
    Finding,
    ModelPosition,
    PreservedAlternative,
    ResearchPlan,
    Source,
    StageSummary,
    SubQuestion,
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


def _stage1_result() -> DecompositionResult:
    return DecompositionResult(
        core_question="What is the evidence?",
        sub_questions=[
            SubQuestion(
                id="Q-1",
                question="What happened?",
                type="empirical",
                research_priority="high",
                search_guidance="official evaluations",
            ),
            SubQuestion(
                id="Q-2",
                question="How should it be interpreted?",
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
        stage_summary=_stage_summary("Stage 1"),
    )


def _stage2_result() -> EvidencePackage:
    return EvidencePackage(
        sub_question_evidence=[],
        total_queries_used=0,
        queries_per_sub_question={"Q-1": 0, "Q-2": 0},
        stage_summary=_stage_summary("Stage 2"),
    )


def _stage4_result(dispute_status: DisputeStatus) -> ClaimExtractionResult:
    return ClaimExtractionResult(
        claim_ledger=[
            ClaimLedgerEntry(
                id="C-1",
                statement="Claim one.",
                source_models=["A"],
                evidence_label=EvidenceLabel.VENDOR_DOCUMENTED,
                source_references=["S-1"],
                status=ClaimStatus.CONTESTED,
                supporting_models=["A"],
                contesting_models=["B"],
                related_assumptions=[],
            )
        ],
        assumption_set=[],
        dispute_queue=[
            DisputeQueueEntry(
                id="D-1",
                type=DisputeType.PREFERENCE_WEIGHTED,
                description="Whether stability should outweigh speed.",
                claims_involved=["C-1"],
                model_positions=[
                    ModelPosition(model_alias="A", position="Prefer stability."),
                    ModelPosition(model_alias="B", position="Prefer speed."),
                ],
                decision_critical=True,
                decision_critical_rationale="Changes the final recommendation.",
                status=dispute_status,
                resolution_routing="stage_6a_user",
            )
        ],
        statistics={
            "total_claims": 1,
            "total_assumptions": 0,
            "total_disputes": 1,
            "disputes_by_type": {"preference_weighted": 1},
            "decision_critical_disputes": 1,
            "claims_per_model": {"A": 1},
        },
        stage_summary=_stage_summary("Stage 4"),
    )


def _stage5_result(dispute_status: DisputeStatus) -> VerificationResult:
    return VerificationResult(
        disputes_investigated=[],
        additional_sources=[],
        updated_claim_ledger=[
            ClaimLedgerEntry(
                id="C-1",
                statement="Claim one.",
                source_models=["A"],
                evidence_label=EvidenceLabel.VENDOR_DOCUMENTED,
                source_references=["S-1"],
                status=ClaimStatus.VERIFIED,
                supporting_models=["A"],
                contesting_models=[],
                related_assumptions=[],
            )
        ],
        updated_dispute_queue=[
            DisputeQueueEntry(
                id="D-1",
                type=DisputeType.PREFERENCE_WEIGHTED,
                description="Whether stability should outweigh speed.",
                claims_involved=["C-1"],
                model_positions=[
                    ModelPosition(model_alias="A", position="Prefer stability."),
                    ModelPosition(model_alias="B", position="Prefer speed."),
                ],
                decision_critical=True,
                decision_critical_rationale="Changes the final recommendation.",
                status=dispute_status,
                resolution_routing="stage_6a_user",
            )
        ],
        search_budget={},
        rounds_used=1,
        stage_summary=_stage_summary("Stage 5"),
    )


def _stage6_result() -> SynthesisReport:
    return SynthesisReport(
        executive_recommendation="Prefer the stable option.",
        conditions_of_validity=["Unless costs dominate."],
        decision_relevant_tradeoffs=[
            Tradeoff(
                if_optimize_for="stability",
                then_recommend="Prefer the stable option.",
            )
        ],
        disagreement_map=[
            DisagreementMapEntry(
                dispute_id="D-1",
                type=DisputeType.PREFERENCE_WEIGHTED,
                summary="Preference split",
                resolution="Deferred to user.",
                action_taken="Stage 6a steering",
                chosen_interpretation="Stability-first",
            )
        ],
        preserved_alternatives=[
            PreservedAlternative(
                alternative="Faster option",
                conditions_for_preference="Use if speed matters most.",
                supporting_claims=["C-1"],
            )
        ],
        key_assumptions=[],
        confidence_assessment=[],
        process_summary=[_stage_summary("Stage 6")],
        claim_ledger_excerpt=[
            {
                "claim_id": "C-1",
                "statement": "Claim one.",
                "final_status": "verified",
                "resolution_path": "Stage 5",
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
        evidence_gaps=[],
        reasoning="Reasoning",
        stage_summary=_stage_summary("Stage 6"),
    )


def test_select_stage6a_steering_disputes_uses_latest_tyler_statuses() -> None:
    """Stage 6a should include deferred-to-user preference disputes."""
    disputes = [
        _stage4_result(DisputeStatus.DEFERRED_TO_USER).dispute_queue[0],
        DisputeQueueEntry(
            id="D-2",
            type=DisputeType.EMPIRICAL,
            description="Empirical dispute",
            claims_involved=["C-1"],
            model_positions=[],
            decision_critical=True,
            decision_critical_rationale="Could matter.",
            status=DisputeStatus.UNRESOLVED,
            resolution_routing="stage_5_evidence",
        ),
    ]

    selected = _select_stage6a_steering_disputes(disputes)

    assert [dispute.id for dispute in selected] == ["D-1"]


@pytest.mark.asyncio
async def test_run_pipeline_collects_guidance_from_stage5_deferred_queue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The live pipeline should prompt on Stage 5's deferred-to-user queue."""
    fixture_path = tmp_path / "bundle.json"
    fixture_path.write_text("{}")

    bundle = EvidenceBundle(
        question=ResearchQuestion(text="Which option should we choose?"),
        sources=[SourceRecord(id="S-1", url="https://example.com/source", title="Source")],
        evidence=[],
        gaps=[],
    )
    stage1 = _stage1_result()
    stage2 = _stage2_result()
    stage4 = _stage4_result(DisputeStatus.DEFERRED_TO_USER)
    stage5 = _stage5_result(DisputeStatus.DEFERRED_TO_USER)
    stage6 = _stage6_result()

    monkeypatch.setattr("engine.configure_run_runtime", lambda run_id, output_dir: {"db_path": None})
    monkeypatch.setattr("engine.load_config", lambda: {"depth": "standard"})
    monkeypatch.setattr("engine.get_depth_config", lambda: {"pipeline_max_budget_usd": 1.0, "compression_threshold": 80})
    monkeypatch.setattr("engine.get_budget", lambda name: 1)
    monkeypatch.setattr("grounded_research.ingest.load_manual_bundle", lambda path: bundle)
    monkeypatch.setattr("grounded_research.ingest.validate_bundle", lambda bundle: [])
    monkeypatch.setattr("grounded_research.compress.compress_evidence", lambda bundle, threshold: 0)
    async def fake_run_analysts_tyler_v1(**kwargs):
        return [], {}, []

    async def fake_canonicalize_tyler_v1(*args, **kwargs):
        return stage4

    async def fake_verify_disputes_tyler_v1(**kwargs):
        return stage5, [], 0

    async def fake_generate_tyler_synthesis_report(*args, **kwargs):
        return stage6

    async def fake_render_long_report(*args, **kwargs):
        return "# Report"

    monkeypatch.setattr("grounded_research.analysts.run_analysts_tyler_v1", fake_run_analysts_tyler_v1)
    monkeypatch.setattr("grounded_research.canonicalize.canonicalize_tyler_v1", fake_canonicalize_tyler_v1)
    monkeypatch.setattr("grounded_research.verify.verify_disputes_tyler_v1", fake_verify_disputes_tyler_v1)
    monkeypatch.setattr("grounded_research.export.generate_tyler_synthesis_report", fake_generate_tyler_synthesis_report)
    monkeypatch.setattr("grounded_research.export.build_tyler_downstream_handoff", lambda state: None)
    monkeypatch.setattr("grounded_research.export.validate_tyler_grounding", lambda *args, **kwargs: [])
    monkeypatch.setattr("grounded_research.export.render_long_report", fake_render_long_report)
    monkeypatch.setattr("grounded_research.export.write_outputs", lambda *args, **kwargs: {})
    monkeypatch.setattr("builtins.input", lambda prompt="": "Prefer the stable option.")

    class _FakeStdin:
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr("engine.sys.stdin", _FakeStdin())

    state = await run_pipeline(
        fixture_path=fixture_path,
        output_dir=tmp_path / "out",
        tyler_stage_1_result=stage1,
        tyler_stage_2_result=stage2,
    )

    assert state.user_guidance_notes == ["D-1: Prefer the stable option."]
