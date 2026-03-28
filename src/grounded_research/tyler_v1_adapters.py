"""Adapters between the shipped runtime models and Tyler V1 literal contracts.

These adapters support the staged literal-parity migration. They make it
possible to generate Tyler-native artifacts without forcing the whole runtime
to switch contracts in one unsafe step. During the migration, Tyler-native
artifacts are treated as the primary contract while the shipped runtime keeps
receiving explicit projected copies where later phases still depend on them.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import logging
import re

from grounded_research.models import ArbitrationResult as RuntimeArbitrationResult, ClaimUpdate as RuntimeClaimUpdate
from grounded_research.tyler_v1_models import (
    AdditionalSource,
    AnalysisObject,
    ArbitrationAssessment,
    AssumptionSetEntry,
    ClaimExtractionResult,
    ClaimLedgerEntry,
    ClaimStatus,
    ClaimStatusUpdate,
    ConfidenceAssessment,
    DecompositionResult,
    DisagreementMapEntry,
    DisputeQueueEntry,
    DisputeStatus,
    DisputeType,
    EvidenceTrailEntry,
    EvidencePackage,
    ExtractionStatistics,
    Finding,
    KeyAssumption,
    ModelPosition,
    PreservedAlternative,
    ResolutionOutcome,
    SynthesisReport,
    Source,
    StageSummary,
    SubQuestion as TylerSubQuestion,
    SubQuestionEvidence,
    Tradeoff,
)

_LOG = logging.getLogger(__name__)


def normalize_tyler_decomposition_ids(result: DecompositionResult) -> DecompositionResult:
    """Normalize Tyler Stage 1 IDs after LLM generation.

    The LLM can override schema descriptions and emit arbitrary IDs. Tyler's
    Stage 1 contract expects `Q-{n}` IDs. This function rewrites malformed IDs
    into deterministic sequential `Q-{n}` values.
    """
    for idx, sub_question in enumerate(result.sub_questions, start=1):
        if not sub_question.id.startswith("Q-"):
            sub_question.id = f"Q-{idx}"
    return result
def normalize_tyler_analysis_object(
    result: AnalysisObject,
    *,
    valid_source_ids: set[str],
    model_alias: str,
    reasoning_frame: str,
) -> AnalysisObject:
    """Repair Tyler Stage 3 IDs and references after LLM generation."""
    claim_id_map: dict[str, str] = {}
    for idx, claim in enumerate(result.claims, start=1):
        claim_id_map[claim.id] = f"C-{idx}"

    normalized_claims = [
        claim.model_copy(
            update={
                "id": claim_id_map[claim.id],
                "source_references": _ordered_unique(
                    [source_id for source_id in claim.source_references if source_id in valid_source_ids]
                ),
            }
        )
        for claim in result.claims
    ]

    assumption_id_map: dict[str, str] = {}
    for idx, assumption in enumerate(result.assumptions, start=1):
        assumption_id_map[assumption.id] = f"A-{idx}"

    normalized_assumptions = [
        assumption.model_copy(
            update={
                "id": assumption_id_map[assumption.id],
                "depends_on_claims": [
                    claim_id_map[claim_id]
                    for claim_id in assumption.depends_on_claims
                    if claim_id in claim_id_map
                ],
            }
        )
        for assumption in result.assumptions
    ]

    evidence_used = _ordered_unique(
        [
            source_id
            for source_id in result.evidence_used
            if source_id in valid_source_ids
        ]
    )
    if not evidence_used:
        evidence_used = _ordered_unique(
            source_id
            for claim in normalized_claims
            for source_id in claim.source_references
        )

    return result.model_copy(
        update={
            "model_alias": model_alias,
            "reasoning_frame": reasoning_frame,
            "claims": normalized_claims,
            "assumptions": normalized_assumptions,
            "evidence_used": evidence_used,
        }
    )
def _ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered
def _compute_resolution_routing(dispute_type: DisputeType, decision_critical: bool) -> str:
    """Match Tyler's deterministic routing table from Stage 4."""
    if not decision_critical:
        return "logged_only"
    if dispute_type is DisputeType.EMPIRICAL:
        return "stage_5_evidence"
    if dispute_type is DisputeType.INTERPRETIVE:
        return "stage_5_arbitration"
    return "stage_6_user_input"


def normalize_tyler_claim_extraction_result(
    result: ClaimExtractionResult,
    *,
    valid_source_ids: set[str],
    allowed_model_aliases: set[str],
) -> ClaimExtractionResult:
    """Repair Tyler Stage 4 IDs and references after LLM generation.

    The Stage 4 contract is strict, but the LLM can still emit malformed IDs,
    unsupported statuses, or invalid source references. This function rewrites
    the artifact into a deterministic, referentially-integral form without
    changing its high-level analytical meaning.
    """
    original_claims = list(result.claim_ledger)
    claim_id_map: dict[str, str] = {}
    for idx, claim in enumerate(original_claims, start=1):
        claim_id_map[claim.id] = f"C-{idx}"

    original_assumptions = list(result.assumption_set)
    assumption_id_map: dict[str, str] = {}
    for idx, assumption in enumerate(original_assumptions, start=1):
        assumption_id_map[assumption.id] = f"A-{idx}"

    normalized_assumptions: list[AssumptionSetEntry] = []
    for old_assumption in original_assumptions:
        new_id = assumption_id_map[old_assumption.id]
        dependent_claims = [
            claim_id_map[claim_id]
            for claim_id in old_assumption.dependent_claims
            if claim_id in claim_id_map
        ]
        source_models = _ordered_unique(
            [alias for alias in old_assumption.source_models if alias in allowed_model_aliases]
        )
        normalized_assumptions.append(
            old_assumption.model_copy(
                update={
                    "id": new_id,
                    "dependent_claims": dependent_claims,
                    "source_models": source_models,
                    "shared_across_models": len(source_models) >= 2,
                }
            )
        )

    assumption_ids = {assumption.id for assumption in normalized_assumptions}
    dispute_claim_ids = {
        claim_id_map[claim_id]
        for dispute in result.dispute_queue
        for claim_id in dispute.claims_involved
        if claim_id in claim_id_map
    }

    normalized_claims: list[ClaimLedgerEntry] = []
    for old_claim in original_claims:
        new_id = claim_id_map[old_claim.id]
        source_models = _ordered_unique(
            [alias for alias in old_claim.source_models if alias in allowed_model_aliases]
        )
        supporting_models = _ordered_unique(
            [alias for alias in old_claim.supporting_models if alias in allowed_model_aliases]
        ) or list(source_models)
        contesting_models = _ordered_unique(
            [alias for alias in old_claim.contesting_models if alias in allowed_model_aliases]
        )
        source_refs = _ordered_unique(
            [source_id for source_id in old_claim.source_references if source_id in valid_source_ids]
        )
        if new_id in dispute_claim_ids:
            status = ClaimStatus.CONTESTED
        elif not source_refs:
            status = ClaimStatus.INSUFFICIENT_EVIDENCE
        elif len(source_models) >= 2:
            status = ClaimStatus.SUPPORTED
        else:
            status = old_claim.status if old_claim.status in {
                ClaimStatus.INITIAL,
                ClaimStatus.SUPPORTED,
                ClaimStatus.CONTESTED,
                ClaimStatus.CONTRADICTED,
                ClaimStatus.INSUFFICIENT_EVIDENCE,
            } else ClaimStatus.SUPPORTED

        normalized_claims.append(
            old_claim.model_copy(
                update={
                    "id": new_id,
                    "source_models": source_models,
                    "supporting_models": supporting_models,
                    "contesting_models": contesting_models,
                    "source_references": source_refs,
                    "related_assumptions": [
                        assumption_id_map[assumption_id]
                        for assumption_id in old_claim.related_assumptions
                        if assumption_id in assumption_id_map and assumption_id_map[assumption_id] in assumption_ids
                    ],
                    "status": status,
                }
            )
        )

    original_disputes = list(result.dispute_queue)
    dispute_id_map: dict[str, str] = {}
    for idx, dispute in enumerate(original_disputes, start=1):
        dispute_id_map[dispute.id] = f"D-{idx}"

    normalized_disputes: list[DisputeQueueEntry] = []
    claim_lookup = {claim.id: claim for claim in normalized_claims}
    for old_dispute in original_disputes:
        new_id = dispute_id_map[old_dispute.id]
        claims_involved = _ordered_unique(
            [claim_id_map[claim_id] for claim_id in old_dispute.claims_involved if claim_id in claim_id_map]
        )
        if not claims_involved:
            continue
        dispute_type = old_dispute.type
        if dispute_type not in {
            DisputeType.EMPIRICAL,
            DisputeType.INTERPRETIVE,
            DisputeType.PREFERENCE_WEIGHTED,
            DisputeType.SPEC_AMBIGUITY,
            DisputeType.OTHER,
        }:
            dispute_type = DisputeType.OTHER
        routing = _compute_resolution_routing(dispute_type, old_dispute.decision_critical)
        if routing == "logged_only":
            status = DisputeStatus.LOGGED_ONLY
        elif routing == "stage_6_user_input":
            status = DisputeStatus.DEFERRED_TO_USER
        else:
            status = DisputeStatus.UNRESOLVED

        model_positions: list[ModelPosition] = []
        for position in old_dispute.model_positions:
            if position.model_alias not in allowed_model_aliases:
                continue
            model_positions.append(position)
        if not model_positions:
            alias_counts = Counter(
                alias
                for claim_id in claims_involved
                for alias in claim_lookup[claim_id].source_models
                if alias in allowed_model_aliases
            )
            model_positions = [
                ModelPosition(
                    model_alias=alias,
                    position=f"Participates in dispute {new_id} via claims {', '.join(claims_involved)}.",
                )
                for alias, _count in alias_counts.most_common()
            ]

        normalized_disputes.append(
            old_dispute.model_copy(
                update={
                    "id": new_id,
                    "type": dispute_type,
                    "claims_involved": claims_involved,
                    "model_positions": model_positions,
                    "status": status,
                    "resolution_routing": routing,
                    "decision_critical_rationale": old_dispute.decision_critical_rationale
                    or "Normalized by orchestrator during Tyler Stage 4 migration.",
                }
            )
        )

    claim_supporting_map: dict[str, set[str]] = {claim.id: set(claim.supporting_models) for claim in normalized_claims}
    claim_contesting_map: dict[str, set[str]] = {claim.id: set(claim.contesting_models) for claim in normalized_claims}
    for dispute in normalized_disputes:
        aliases_in_dispute = {
            position.model_alias
            for position in dispute.model_positions
            if position.model_alias in allowed_model_aliases
        }
        for claim_id in dispute.claims_involved:
            claim = claim_lookup.get(claim_id)
            if claim is None:
                continue
            supporting_aliases = set(claim.source_models) or aliases_in_dispute
            claim_supporting_map[claim_id].update(supporting_aliases)
            claim_contesting_map[claim_id].update(aliases_in_dispute - supporting_aliases)

    final_claims: list[ClaimLedgerEntry] = []
    for claim in normalized_claims:
        supporting_models = _ordered_unique(list(claim_supporting_map[claim.id]))
        contesting_models = _ordered_unique(list(claim_contesting_map[claim.id]))
        final_claims.append(
            claim.model_copy(
                update={
                    "supporting_models": supporting_models,
                    "contesting_models": contesting_models,
                }
            )
        )

    stats = ExtractionStatistics(
        total_claims=len(final_claims),
        total_assumptions=len(normalized_assumptions),
        total_disputes=len(normalized_disputes),
        disputes_by_type=dict(Counter(dispute.type.value for dispute in normalized_disputes)),
        decision_critical_disputes=sum(1 for dispute in normalized_disputes if dispute.decision_critical),
        claims_per_model=dict(
            Counter(
                alias
                for claim in final_claims
                for alias in claim.source_models
            )
        ),
    )

    return result.model_copy(
        update={
            "claim_ledger": final_claims,
            "assumption_set": normalized_assumptions,
            "dispute_queue": normalized_disputes,
            "statistics": stats,
        }
    )
def tyler_assessment_to_current_arbitration(
    assessment: ArbitrationAssessment,
    additional_sources: list[AdditionalSource],
) -> RuntimeArbitrationResult:
    """Project one Tyler arbitration assessment into the shipped runtime artifact."""
    verdict = {
        ResolutionOutcome.CLAIM_SUPPORTED: "supported",
        ResolutionOutcome.CLAIM_REFUTED: "refuted",
        ResolutionOutcome.INTERPRETATION_REVISED: "revised",
        ResolutionOutcome.EVIDENCE_INSUFFICIENT: "inconclusive",
    }[assessment.resolution]

    source_ids = [source.source_id for source in additional_sources if source.retrieved_for_dispute == assessment.dispute_id]
    status_map = {
        ClaimStatus.VERIFIED: "supported",
        ClaimStatus.REFUTED: "refuted",
        ClaimStatus.UNRESOLVED: "inconclusive",
    }
    return RuntimeArbitrationResult(
        dispute_id=assessment.dispute_id,
        verdict=verdict,
        new_evidence_ids=source_ids,
        reasoning=assessment.reasoning,
        claim_updates=[
            RuntimeClaimUpdate(
                claim_id=update.claim_id,
                new_status=status_map.get(update.new_status, "revised"),
                basis_type="new_evidence",
                cited_evidence_ids=source_ids,
                justification=update.remaining_uncertainty or assessment.new_evidence_summary,
            )
            for update in assessment.updated_claim_statuses
        ],
    )


def render_tyler_synthesis_markdown(report: SynthesisReport, original_query: str) -> str:
    """Render Tyler's structured synthesis artifact as the final markdown report."""
    lines = [
        f"# {original_query}",
        "",
        "## Executive Recommendation",
        "",
        report.executive_recommendation,
        "",
        "## Conditions Of Validity",
        "",
    ]
    for condition in report.conditions_of_validity:
        lines.append(f"- {condition}")
    lines.extend(["", "## Decision-Relevant Tradeoffs", ""])
    for tradeoff in report.decision_relevant_tradeoffs:
        lines.append(f"- If optimize for **{tradeoff.if_optimize_for}**: {tradeoff.then_recommend}")
    lines.extend(["", "## Disagreement Map", ""])
    for item in report.disagreement_map:
        lines.append(f"- **{item.dispute_id}** [{item.type.value}] {item.summary}")
        lines.append(f"  Resolution: {item.resolution}")
        lines.append(f"  Action taken: {item.action_taken}")
        if item.chosen_interpretation:
            lines.append(f"  Chosen interpretation: {item.chosen_interpretation}")
    lines.extend(["", "## Preserved Alternatives", ""])
    for alternative in report.preserved_alternatives:
        lines.append(f"- **{alternative.alternative}**")
        lines.append(f"  When better: {alternative.conditions_for_preference}")
        lines.append(f"  Supporting claims: {', '.join(alternative.supporting_claims)}")
    lines.extend(["", "## Key Assumptions", ""])
    for assumption in report.key_assumptions:
        lines.append(f"- **{assumption.assumption_id}** {assumption.statement}")
        lines.append(f"  If wrong: {assumption.if_wrong}")
    lines.extend(["", "## Confidence Assessment", ""])
    for item in report.confidence_assessment:
        lines.append(f"- **{item.confidence.value.upper()}**: {item.claim_summary}")
        lines.append(f"  Basis: {item.basis}")
    lines.extend(["", "## Process Summary", ""])
    for summary in report.process_summary:
        lines.append(f"### {summary.stage_name}")
        lines.append(f"- Goal: {summary.goal}")
        for finding in summary.key_findings:
            lines.append(f"- {finding}")
        for decision in summary.decisions_made:
            lines.append(f"- Decision: {decision}")
        lines.append(f"- Outcome: {summary.outcome}")
    lines.extend(["", "## Claim Ledger Excerpt", ""])
    for claim in report.claim_ledger_excerpt:
        lines.append(f"- **{claim.claim_id}** [{claim.final_status.value}] {claim.statement}")
        lines.append(f"  Resolution path: {claim.resolution_path}")
    lines.extend(["", "## Evidence Trail", ""])
    for source in report.evidence_trail:
        lines.append(f"- **{source.source_id}** ({source.quality_score:.2f}) {source.key_contribution}")
        lines.append(f"  URL: {source.url}")
        if source.conflicts_resolved:
            lines.append(f"  Helped resolve: {', '.join(source.conflicts_resolved)}")
    lines.extend(["", "## Evidence Gaps", ""])
    for gap in report.evidence_gaps:
        lines.append(f"- {gap}")
    lines.extend(["", "## Synthesis Reasoning", "", report.reasoning, ""])
    return "\n".join(lines)
