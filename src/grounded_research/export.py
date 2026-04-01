"""Canonical Tyler-native export and downstream handoff.

This module owns the final export boundary for the live runtime:

1. Generate Tyler Stage 6 `SynthesisReport`
2. Render `report.md` directly from Stage 6
3. Render `summary.md` directly from Stage 6
4. Emit `handoff.json` as a Tyler-native downstream artifact

Legacy `FinalReport` and legacy handoff surfaces are intentionally excluded from
the live export path so the repo keeps one canonical output contract.
"""

from __future__ import annotations

import logging
from pathlib import Path

from grounded_research.config import (
    get_fallback_models,
    get_model,
    get_tyler_literal_parity_config,
)
from grounded_research.models import (
    EvidenceBundle,
    PipelineState,
    TylerDownstreamHandoff,
)
from grounded_research.tyler_v1_adapters import render_tyler_synthesis_markdown
from grounded_research.tyler_v1_models import SynthesisReport, VerificationResult

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LOG = logging.getLogger(__name__)


def validate_tyler_grounding(
    report: SynthesisReport,
    *,
    verification_result: VerificationResult,
    bundle: EvidenceBundle,
) -> list[str]:
    """Validate the canonical Tyler Stage 6 artifact against Stage 5 and sources."""
    errors: list[str] = []
    claim_map = {claim.id: claim for claim in verification_result.updated_claim_ledger}
    source_ids = {source.id for source in bundle.sources}
    source_ids.update(source.source_id for source in verification_result.additional_sources)

    for excerpt in report.claim_ledger_excerpt:
        claim = claim_map.get(excerpt.claim_id)
        if claim is None:
            errors.append(f"Claim excerpt {excerpt.claim_id} not found in Tyler Stage 5 ledger")
            continue
        if not claim.source_references:
            errors.append(
                f"Claim excerpt {excerpt.claim_id} has no source references in Tyler Stage 5 ledger"
            )
            continue
        missing_refs = [source_id for source_id in claim.source_references if source_id not in source_ids]
        if missing_refs:
            errors.append(
                f"Claim excerpt {excerpt.claim_id} references unknown sources: {', '.join(missing_refs)}"
            )

    evidence_trail_ids = {source.source_id for source in report.evidence_trail}
    unknown_trail_ids = sorted(evidence_trail_ids - source_ids)
    for source_id in unknown_trail_ids:
        errors.append(f"Evidence trail source {source_id} not found in Stage 2/5 source inventory")

    unresolved_dispute_ids = {
        dispute.id
        for dispute in verification_result.updated_dispute_queue
        if dispute.status is not None and dispute.status.value == "unresolved"
    }
    mentioned_dispute_ids = {entry.dispute_id for entry in report.disagreement_map}
    missing_disputes = sorted(unresolved_dispute_ids - mentioned_dispute_ids)
    for dispute_id in missing_disputes:
        errors.append(f"Unresolved Tyler dispute {dispute_id} not mentioned in disagreement_map")

    return errors


def _validate_tyler_synthesis_report(
    report: SynthesisReport,
    *,
    unresolved_dispute_ids: set[str],
    min_tradeoffs: int,
    min_preserved_alternatives: int,
) -> list[str]:
    """Return repair feedback for underfilled Tyler Stage 6 outputs."""
    errors: list[str] = []
    if len(report.decision_relevant_tradeoffs) < min_tradeoffs:
        errors.append(
            "decision_relevant_tradeoffs is underfilled. Add concrete decision tradeoffs tied to the recommendation and evidence."
        )
    if len(report.preserved_alternatives) < min_preserved_alternatives:
        errors.append(
            "preserved_alternatives is underfilled. Preserve at least one viable alternative when different conditions would rationally change the recommendation."
        )
    disagreement_ids = {entry.dispute_id for entry in report.disagreement_map}
    missing_unresolved = sorted(unresolved_dispute_ids - disagreement_ids)
    if missing_unresolved:
        errors.append(
            "disagreement_map is missing unresolved disputes: " + ", ".join(missing_unresolved)
        )
    return errors


def build_tyler_downstream_handoff(state: PipelineState) -> TylerDownstreamHandoff:
    """Build the canonical Tyler-native downstream artifact."""
    assert state.question is not None
    assert state.tyler_stage_2_result is not None
    assert state.tyler_stage_5_result is not None
    assert state.tyler_stage_6_result is not None
    return TylerDownstreamHandoff(
        question=state.question,
        stage_2_evidence_package=state.tyler_stage_2_result,
        stage_5_verification_result=state.tyler_stage_5_result,
        stage_6_synthesis_report=state.tyler_stage_6_result,
    )


async def generate_tyler_synthesis_report(
    state: PipelineState,
    *,
    trace_id: str,
    max_budget: float = 1.0,
) -> SynthesisReport:
    """Run Tyler's literal Stage 6 synthesis contract."""
    from llm_client import acall_llm_structured, render_prompt

    assert state.tyler_stage_4_result is not None
    assert state.tyler_stage_5_result is not None
    assert state.evidence_bundle is not None
    assert state.question is not None
    parity_policy = get_tyler_literal_parity_config()

    if state.tyler_stage_1_result is not None:
        tyler_stage1 = state.tyler_stage_1_result
    else:
        from grounded_research.decompose import decompose_question_tyler_v1

        tyler_stage1 = await decompose_question_tyler_v1(
            question=state.question.text,
            trace_id=f"{trace_id}/stage1_for_synthesis",
            max_budget=max_budget * 0.15,
        )

    stage_2_result = state.tyler_stage_2_result
    if stage_2_result is None:
        raise ValueError(
            "Tyler Stage 6 requires a canonical Tyler Stage 2 EvidencePackage in PipelineState. "
            "Populate `state.tyler_stage_2_result` from the live pipeline or fixture artifacts "
            "instead of rebuilding it from the legacy EvidenceBundle."
        )
    stage_4_result = state.tyler_stage_4_result
    stage_5_result = state.tyler_stage_5_result

    decision_critical_claim_ids = {
        claim_id
        for dispute in stage_5_result.updated_dispute_queue
        if dispute.decision_critical
        for claim_id in dispute.claims_involved
    }
    grounded_claim_ids = {
        claim.id
        for claim in stage_5_result.updated_claim_ledger
        if claim.source_references
    }
    decision_critical_claims = [
        claim
        for claim in stage_5_result.updated_claim_ledger
        if claim.id in decision_critical_claim_ids and claim.id in grounded_claim_ids
    ]
    noncritical_claims = [
        claim
        for claim in stage_5_result.updated_claim_ledger
        if claim.id not in decision_critical_claim_ids and claim.id in grounded_claim_ids
    ]

    assessment_by_dispute = {
        assessment.dispute_id: assessment for assessment in stage_5_result.disputes_investigated
    }
    dispute_queue_context: list[dict[str, object]] = []
    for dispute in stage_5_result.updated_dispute_queue:
        assessment = assessment_by_dispute.get(dispute.id)
        remaining_uncertainty = ""
        if assessment:
            remaining_bits = [
                update.remaining_uncertainty
                for update in assessment.updated_claim_statuses
                if update.remaining_uncertainty
            ]
            remaining_uncertainty = "; ".join(bit for bit in remaining_bits if bit)
        dispute_queue_context.append(
            {
                **dispute.model_dump(mode="json"),
                "resolution_details": assessment.reasoning if assessment else "",
                "remaining_uncertainty": remaining_uncertainty or dispute.description,
            }
        )

    additional_source_ids = {source.source_id: source for source in stage_5_result.additional_sources}
    top_sources: list[dict[str, object]] = []
    for source in state.evidence_bundle.sources:
        contribution_claims = [
            claim.id
            for claim in stage_5_result.updated_claim_ledger
            if source.id in claim.source_references
        ]
        resolved_disputes = [
            dispute.id
            for dispute in stage_5_result.updated_dispute_queue
            if dispute.status is not None and dispute.id in {
                assessment.dispute_id for assessment in stage_5_result.disputes_investigated
            }
            and source.id in additional_source_ids
        ]
        if not contribution_claims and source.id not in additional_source_ids:
            continue
        top_sources.append(
            {
                "id": source.id,
                "title": source.title,
                "quality_score": {
                    "authoritative": 1.0,
                    "reliable": 0.7,
                    "unknown": 0.5,
                    "unreliable": 0.3,
                }.get(source.quality_tier, 0.5),
                "source_type": source.source_type,
                "contribution_summary": (
                    f"Supports claims {', '.join(contribution_claims[:4])}"
                    if contribution_claims
                    else "Retrieved during Stage 5 targeted verification."
                ),
                "conflicts_resolved": resolved_disputes,
            }
        )
    top_sources = top_sources[:12]

    evidence_gaps = list(
        dict.fromkeys(
            list(state.evidence_bundle.gaps)
            + [
                update.remaining_uncertainty
                for assessment in stage_5_result.disputes_investigated
                for update in assessment.updated_claim_statuses
                if update.remaining_uncertainty
            ]
        )
    )

    stage_3_results = list(state.tyler_stage_3_results)
    stage_3_summary = {
        "stage_name": "Stage 3: Independent Candidate Generation",
        "goal": "Produce independent recommendations, claims, assumptions, and counterarguments from the evidence package.",
        "key_findings": [
            f"{len(stage_3_results)} analysts succeeded",
            f"{sum(len(result.claims) for result in stage_3_results)} total Tyler analyst claims produced",
            "Independent analyst diversity preserved through aliasing and frame separation",
        ],
        "decisions_made": [
            "Preserved only successful Tyler Stage 3 analysis objects for synthesis context",
            "Kept analyst disagreement structure explicit for downstream Stage 4 extraction",
        ],
        "outcome": "Independent analysis objects available for canonicalization.",
        "reasoning": "Combined stage summary synthesized from successful Tyler Stage 3 analysis objects.",
    }
    all_stage_summaries = [
        tyler_stage1.stage_summary.model_dump(mode="json"),
        stage_2_result.stage_summary.model_dump(mode="json"),
        stage_3_summary,
        stage_4_result.stage_summary.model_dump(mode="json"),
        stage_5_result.stage_summary.model_dump(mode="json"),
    ]

    user_clarifications = "\n".join(state.user_guidance_notes)

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "tyler_v1_synthesis.yaml"),
        original_query=state.question.text,
        stage_6_user_input=user_clarifications,
        decision_critical_claims=[claim.model_dump(mode="json") for claim in decision_critical_claims],
        noncritical_claims=[claim.model_dump(mode="json") for claim in noncritical_claims],
        assumption_set=[assumption.model_dump(mode="json") for assumption in stage_4_result.assumption_set],
        dispute_queue=dispute_queue_context,
        top_sources=top_sources,
        evidence_gaps=evidence_gaps,
        all_stage_summaries=all_stage_summaries,
        response_schema_json=SynthesisReport.model_json_schema(),
    )

    unresolved_dispute_ids = {
        dispute.id
        for dispute in stage_5_result.updated_dispute_queue
        if dispute.status is not None and dispute.status.value == "unresolved"
    }

    async def _generate_once(feedback: list[str], suffix: str) -> SynthesisReport:
        prompt_messages = messages
        if feedback:
            prompt_messages = prompt_messages + [
                {
                    "role": "user",
                    "content": "Repair feedback for the previous draft:\n- " + "\n- ".join(feedback),
                }
            ]
        report, _meta = await acall_llm_structured(
            get_model("synthesis"),
            prompt_messages,
            response_model=SynthesisReport,
            task="synthesis_tyler_v1",
            trace_id=f"{trace_id}/synthesis_tyler_v1{suffix}",
            max_budget=max_budget,
            fallback_models=get_fallback_models("synthesis"),
        )
        return report

    report = await _generate_once(feedback=[], suffix="")
    if bool(parity_policy.get("stage6_repair_on_underfilled_fields", True)):
        max_repairs = int(parity_policy.get("stage6_repair_attempts", 1))
        for attempt in range(1, max_repairs + 1):
            repair_feedback = _validate_tyler_synthesis_report(
                report,
                unresolved_dispute_ids=unresolved_dispute_ids,
                min_tradeoffs=int(parity_policy.get("stage6_min_tradeoffs", 1)),
                min_preserved_alternatives=int(
                    parity_policy.get("stage6_min_preserved_alternatives", 1)
                ),
            )
            if not repair_feedback:
                break
            _LOG.warning(
                "Tyler Stage 6 synthesis underfilled critical fields; retrying once. errors=%s",
                repair_feedback,
            )
            report = await _generate_once(
                feedback=repair_feedback,
                suffix=f"/repair_{attempt}",
            )
    return report


def _render_tyler_structured_summary(report: SynthesisReport, original_query: str) -> str:
    """Render Tyler Stage 6 as a concise summary artifact."""
    lines = [
        f"# {original_query}",
        "",
        "## Executive Recommendation",
        "",
        report.executive_recommendation,
        "",
    ]

    if report.conditions_of_validity:
        lines.extend(["## Conditions Of Validity", ""])
        for condition in report.conditions_of_validity:
            lines.append(f"- {condition}")
        lines.append("")

    if report.decision_relevant_tradeoffs:
        lines.extend(["## Decision-Relevant Tradeoffs", ""])
        for tradeoff in report.decision_relevant_tradeoffs:
            lines.append(
                f"- If optimize for **{tradeoff.if_optimize_for}**: {tradeoff.then_recommend}"
            )
        lines.append("")

    if report.preserved_alternatives:
        lines.extend(["## Preserved Alternatives", ""])
        for alternative in report.preserved_alternatives:
            lines.append(
                f"- **{alternative.alternative}**: {alternative.conditions_for_preference}"
            )
        lines.append("")

    if report.disagreement_map:
        lines.extend(["## Disagreement Map", ""])
        for entry in report.disagreement_map:
            lines.append(f"- **{entry.dispute_id}** [{entry.type.value}] {entry.summary}")
        lines.append("")

    if report.claim_ledger_excerpt:
        lines.extend(["## Claim Ledger Excerpt", ""])
        for claim in report.claim_ledger_excerpt:
            lines.append(f"- **{claim.claim_id}** [{claim.final_status.value}] {claim.statement}")
        lines.append("")

    if report.evidence_gaps:
        lines.extend(["## Evidence Gaps", ""])
        for gap in report.evidence_gaps:
            lines.append(f"- {gap}")
        lines.append("")

    return "\n".join(lines)


async def render_long_report(
    state: PipelineState,
    trace_id: str,
    max_budget: float = 2.0,
) -> str:
    """Render the canonical long-form report directly from Tyler Stage 6."""
    del trace_id, max_budget
    if state.tyler_stage_6_result is None or state.question is None:
        raise ValueError(
            "Canonical long-report rendering requires `state.tyler_stage_6_result` and "
            "`state.question`. Generate Tyler Stage 6 before calling render_long_report()."
        )
    return render_tyler_synthesis_markdown(
        state.tyler_stage_6_result,
        original_query=state.question.text,
    )


def write_outputs(
    state: PipelineState,
    output_dir: Path,
    long_report_md: str | None = None,
) -> dict[str, Path]:
    """Write canonical Tyler-native output artifacts to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    trace_path = output_dir / "trace.json"
    trace_path.write_text(state.model_dump_json(indent=2))
    paths["trace"] = trace_path

    if long_report_md:
        report_path = output_dir / "report.md"
        report_path.write_text(long_report_md)
        paths["report"] = report_path

    if state.tyler_stage_6_result is not None and state.question is not None:
        summary_path = output_dir / "summary.md"
        summary_path.write_text(
            _render_tyler_structured_summary(
                state.tyler_stage_6_result,
                state.question.text,
            )
        )
        paths["summary"] = summary_path

    if state.tyler_handoff is not None:
        handoff = state.tyler_handoff
    elif (
        state.question is not None
        and state.tyler_stage_2_result is not None
        and state.tyler_stage_5_result is not None
        and state.tyler_stage_6_result is not None
    ):
        handoff = build_tyler_downstream_handoff(state)
    else:
        handoff = None

    if handoff is not None:
        handoff_path = output_dir / "handoff.json"
        handoff_path.write_text(handoff.model_dump_json(indent=2))
        paths["handoff"] = handoff_path

    return paths
