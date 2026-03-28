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

from grounded_research.models import (
    AnalystRun,
    ArbitrationResult as RuntimeArbitrationResult,
    Counterargument as RuntimeCounterargument,
    Claim as RuntimeClaim,
    ClaimLedger,
    ClaimUpdate as RuntimeClaimUpdate,
    Dispute as RuntimeDispute,
    EvidenceBundle,
    FinalReport,
    QuestionDecomposition,
    RawClaim,
    Recommendation,
    Assumption as RuntimeAssumption,
    SubQuestion as CurrentSubQuestion,
    _make_id,
)
from grounded_research.tyler_v1_models import (
    AdditionalSource,
    AnalysisObject,
    ArbitrationAssessment,
    Assumption,
    AssumptionSetEntry,
    ClaimExtractionResult,
    ClaimLedgerEntry,
    ClaimStatus,
    ClaimStatusUpdate,
    ConfidenceLevel,
    ConfidenceAssessment,
    CounterArgument,
    DecompositionResult,
    DisagreementMapEntry,
    DisputeQueueEntry,
    DisputeStatus,
    DisputeType,
    EvidenceTrailEntry,
    EvidenceLabel,
    EvidencePackage,
    ExtractionStatistics,
    Finding,
    Claim as TylerClaim,
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
    VerificationResult,
)

_LOG = logging.getLogger(__name__)


def current_to_tyler_sub_question_id_map(
    current_decomposition: QuestionDecomposition,
    tyler_decomposition: DecompositionResult,
) -> dict[str, str]:
    """Translate current runtime sub-question IDs into Tyler Stage 1 IDs.

    Fixture bundles often preserve the shipped runtime's `SQ-*` sub-question
    IDs while the Tyler-native Stage 1 decomposition uses canonical `Q-*`
    IDs. The runtime migration keeps sub-questions in positional lockstep, so
    position is the correct bridge while both representations coexist.
    """
    if len(current_decomposition.sub_questions) != len(tyler_decomposition.sub_questions):
        raise ValueError(
            "Current and Tyler decompositions must have the same number of sub-questions "
            "to translate fixture evidence IDs."
        )
    return {
        current_sub_question.id: tyler_sub_question.id
        for current_sub_question, tyler_sub_question in zip(
            current_decomposition.sub_questions,
            tyler_decomposition.sub_questions,
            strict=True,
        )
    }


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


def tyler_decomposition_to_current(result: DecompositionResult) -> QuestionDecomposition:
    """Convert Tyler's Stage 1 artifact into the current runtime decomposition.

    This keeps the runtime operational while Stage 1 begins migrating toward the
    literal Tyler contract.
    """
    type_map = {
        "empirical": "factual",
        "interpretive": "evaluative",
        "preference": "evaluative",
    }
    return QuestionDecomposition(
        core_question=result.core_question,
        sub_questions=[
            CurrentSubQuestion(
                id=sq.id,
                text=sq.question,
                type=type_map.get(sq.type, "scope"),
                falsification_target=(
                    result.research_plan.falsification_targets[idx]
                    if idx < len(result.research_plan.falsification_targets)
                    else "N/A"
                ),
            )
            for idx, sq in enumerate(result.sub_questions)
        ],
        optimization_axes=result.optimization_axes,
        research_plan=(
            "Verify: "
            + "; ".join(result.research_plan.what_to_verify)
            + ". Critical sources: "
            + ", ".join(result.research_plan.critical_source_types)
        ),
        ambiguous_terms=[],
    )


def current_decomposition_to_tyler(
    decomposition: QuestionDecomposition,
    original_query: str,
) -> DecompositionResult:
    """Convert the shipped decomposition artifact into Tyler's Stage 1 contract."""
    type_map = {
        "factual": "empirical",
        "causal": "empirical",
        "comparative": "interpretive",
        "evaluative": "interpretive",
        "scope": "preference",
    }
    critical_source_types = list(
        dict.fromkeys(
            phrase.strip()
            for phrase in re.split(r"[;,]", decomposition.research_plan)
            if phrase.strip()
        )
    )[:4]
    if not critical_source_types:
        critical_source_types = ["official docs", "benchmarks"]

    return DecompositionResult(
        core_question=decomposition.core_question or original_query,
        sub_questions=[
            TylerSubQuestion(
                id=f"Q-{idx}",
                question=sq.text,
                type=type_map.get(sq.type, "interpretive"),
                research_priority="high" if idx == 1 else "medium",
                search_guidance=sq.falsification_target or "Find high-quality evidence that would change the answer.",
            )
            for idx, sq in enumerate(decomposition.sub_questions, start=1)
        ],
        optimization_axes=decomposition.optimization_axes,
        research_plan={
            "what_to_verify": [sq.text for sq in decomposition.sub_questions[:3]],
            "critical_source_types": critical_source_types,
            "falsification_targets": [
                sq.falsification_target or "Contradictory high-quality evidence"
                for sq in decomposition.sub_questions
            ],
        },
        stage_summary={
            "stage_name": "Stage 1: Intake & Decomposition",
            "goal": "Adapt the shipped decomposition into Tyler's literal Stage 1 contract.",
            "key_findings": [
                f"{len(decomposition.sub_questions)} current sub-questions preserved",
                "Optimization axes and falsification targets carried forward",
                "Type mapping from current decomposition is an explicit migration bridge",
            ],
            "decisions_made": [
                "Mapped current sub-question taxonomy onto Tyler's Stage 1 taxonomy",
                "Projected the current research_plan string into Tyler's structured research_plan",
            ],
            "outcome": f"Tyler DecompositionResult for query: {original_query[:80]}",
            "reasoning": "Adapter conversion from current QuestionDecomposition into Tyler's Stage 1 contract.",
        },
    )


def _quality_tier_to_score(quality_tier: str) -> float:
    """Map current qualitative source tiers onto Tyler's numeric quality score."""
    return {
        "authoritative": 0.9,
        "reliable": 0.75,
        "unknown": 0.5,
        "unreliable": 0.2,
    }.get(quality_tier, 0.5)


def _current_source_to_evidence_label(source_type: str) -> EvidenceLabel:
    """Approximate Tyler evidence labels from current source metadata."""
    if source_type in {"government_db", "primary_document", "academic"}:
        return EvidenceLabel.VENDOR_DOCUMENTED
    if source_type in {"news", "web_search"}:
        return EvidenceLabel.EMPIRICALLY_OBSERVED
    if source_type in {"platform_transparency", "social_media"}:
        return EvidenceLabel.MODEL_SELF_CHARACTERIZATION
    return EvidenceLabel.SPECULATIVE_INFERENCE


def current_bundle_to_tyler_evidence_package(
    bundle: EvidenceBundle,
    decomposition: DecompositionResult,
    *,
    current_decomposition: QuestionDecomposition | None = None,
) -> EvidencePackage:
    """Convert the current flat evidence bundle into Tyler's Stage 2 artifact."""
    current_sources = {source.id: source for source in bundle.sources}
    findings_by_subq_source: dict[tuple[str, str], list[Finding]] = defaultdict(list)

    tyler_question_ids = [sq.id for sq in decomposition.sub_questions]
    if not tyler_question_ids:
        raise ValueError("Tyler decomposition must include at least one sub-question.")
    current_to_tyler_ids = (
        current_to_tyler_sub_question_id_map(current_decomposition, decomposition)
        if current_decomposition is not None
        else {}
    )

    for item in bundle.evidence:
        source = current_sources.get(item.source_id)
        if source is None:
            continue
        target_sub_questions = item.sub_question_ids or [tyler_question_ids[0]]
        for sub_question_id in target_sub_questions:
            translated_sub_question_id = current_to_tyler_ids.get(sub_question_id, sub_question_id)
            findings_by_subq_source[(translated_sub_question_id, source.id)].append(
                Finding(
                    finding=item.content,
                    evidence_label=_current_source_to_evidence_label(source.source_type),
                    original_quote=item.content if item.content_type in {"quotation", "data_point"} else None,
                )
            )

    sub_question_evidence: list[SubQuestionEvidence] = []
    for sub_question in decomposition.sub_questions:
        sources: list[Source] = []
        for source_id, source in current_sources.items():
            findings = findings_by_subq_source.get((sub_question.id, source_id))
            if not findings:
                continue
            sources.append(
                Source(
                    id=source.id,
                    url=source.url,
                    title=source.title,
                    source_type=source.source_type,
                    quality_score=_quality_tier_to_score(source.quality_tier),
                    publication_date=source.published_at.date().isoformat() if source.published_at else None,
                    retrieval_date=source.retrieved_at.date().isoformat(),
                    key_findings=findings,
                )
            )
        sub_question_evidence.append(
            SubQuestionEvidence(
                sub_question_id=sub_question.id,
                sources=sources,
                meets_sufficiency=len(sources) >= 2,
                gap_description=None if len(sources) >= 2 else f"Fewer than 2 sources found for {sub_question.id}",
            )
        )

    queries_per_sub_question = {
        sub_question.id: 0
        for sub_question in decomposition.sub_questions
    }
    return EvidencePackage(
        sub_question_evidence=sub_question_evidence,
        total_queries_used=0,
        queries_per_sub_question=queries_per_sub_question,
        stage_summary=decomposition.stage_summary.model_copy(
            update={
                "stage_name": "Stage 2: Broad Retrieval & Evidence Normalization",
                "goal": "Assemble evidence by sub-question in Tyler's Stage 2 artifact shape.",
                "key_findings": [
                    f"{len(bundle.sources)} current sources adapted into Tyler Stage 2 shape",
                    f"{len(bundle.evidence)} current evidence items converted into findings",
                    "Quality score and evidence label mapping are adapter approximations during migration",
                ],
                "decisions_made": [
                    "Grouped evidence by Tyler sub-question ID",
                    "Derived Tyler findings from current evidence items",
                ],
                "outcome": f"{len(sub_question_evidence)} sub-question evidence groups",
                "reasoning": "Adapter conversion from current flat EvidenceBundle into Tyler's grouped EvidencePackage contract.",
            }
        ),
    )


def _current_confidence_to_tyler(confidence: str) -> ConfidenceLevel:
    """Map current confidence strings onto Tyler's enum."""
    return {
        "high": ConfidenceLevel.HIGH,
        "medium": ConfidenceLevel.MEDIUM,
        "low": ConfidenceLevel.LOW,
    }.get(confidence, ConfidenceLevel.MEDIUM)


def current_analyst_run_to_tyler_analysis(
    run: AnalystRun,
    bundle: EvidenceBundle,
    model_alias: str,
    reasoning_frame: str,
) -> AnalysisObject:
    """Convert the current analyst runtime output into Tyler's Stage 3 artifact."""
    evidence_lookup = {item.id: item for item in bundle.evidence}

    def evidence_ids_to_source_ids(evidence_ids: list[str]) -> list[str]:
        seen: list[str] = []
        for evidence_id in evidence_ids:
            source_id = evidence_lookup.get(evidence_id).source_id if evidence_id in evidence_lookup else None
            if source_id and source_id not in seen:
                seen.append(source_id)
        return seen

    def evidence_ids_to_label(evidence_ids: list[str]) -> EvidenceLabel:
        source_ids = evidence_ids_to_source_ids(evidence_ids)
        if not source_ids:
            return EvidenceLabel.SPECULATIVE_INFERENCE
        labels = [
            _current_source_to_evidence_label(source.source_type)
            for source in bundle.sources
            if source.id in source_ids
        ]
        if EvidenceLabel.VENDOR_DOCUMENTED in labels:
            return EvidenceLabel.VENDOR_DOCUMENTED
        if EvidenceLabel.EMPIRICALLY_OBSERVED in labels:
            return EvidenceLabel.EMPIRICALLY_OBSERVED
        if EvidenceLabel.MODEL_SELF_CHARACTERIZATION in labels:
            return EvidenceLabel.MODEL_SELF_CHARACTERIZATION
        return EvidenceLabel.SPECULATIVE_INFERENCE

    counter = run.counterarguments[0] if run.counterarguments else None
    strongest_evidence_against = ""
    if counter:
        for evidence_id in counter.evidence_ids:
            item = evidence_lookup.get(evidence_id)
            if item is not None:
                strongest_evidence_against = item.content
                break

    return AnalysisObject(
        model_alias=model_alias,
        reasoning_frame=reasoning_frame,
        recommendation=run.recommendations[0].statement if run.recommendations else run.summary,
        claims=[
            TylerClaim(
                id=f"C-{idx}",
                statement=claim.statement,
                evidence_label=evidence_ids_to_label(claim.evidence_ids),
                source_references=evidence_ids_to_source_ids(claim.evidence_ids),
                confidence=_current_confidence_to_tyler(claim.confidence),
            )
            for idx, claim in enumerate(run.claims, start=1)
        ],
        assumptions=[
            Assumption(
                id=f"A-{idx}",
                statement=assumption.statement,
                depends_on_claims=run.recommendations[0].supporting_claim_ids if run.recommendations else [],
                if_wrong_impact=assumption.basis or "Would weaken the recommendation if false.",
            )
            for idx, assumption in enumerate(run.assumptions, start=1)
        ],
        evidence_used=[
            source_id
            for source_id in dict.fromkeys(
                source_id
                for claim in run.claims
                for source_id in evidence_ids_to_source_ids(claim.evidence_ids)
            )
        ],
        counter_argument=CounterArgument(
            argument=counter.argument if counter else "No counterargument returned.",
            strongest_evidence_against=strongest_evidence_against or "No specific opposing evidence was cited.",
            counter_confidence=_current_confidence_to_tyler(run.claims[0].confidence if run.claims else "medium"),
        ),
        falsification_conditions=[
            counter.argument if counter else "Material contradictory evidence would change the recommendation."
        ],
        reasoning=run.summary,
        stage_summary={
            "stage_name": "Stage 3: Independent Candidate Generation",
            "goal": "Convert one analyst's reasoning into Tyler's Stage 3 analysis artifact.",
            "key_findings": [
                f"{len(run.claims)} claims adapted from current analyst output",
                f"{len(run.assumptions)} assumptions adapted",
                "Counterargument and source lineage preserved through adapter mapping",
            ],
            "decisions_made": [
                "Mapped evidence IDs to Tyler source references",
                "Approximated evidence labels from current source metadata",
            ],
            "outcome": f"Tyler AnalysisObject for alias {model_alias}",
            "reasoning": "Adapter conversion from current AnalystRun into Tyler's Stage 3 contract.",
        },
    )


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


def tyler_analysis_to_current_analyst_run(
    analysis: AnalysisObject,
    bundle: EvidenceBundle,
    *,
    analyst_label: str,
    model_name: str,
) -> AnalystRun:
    """Project Tyler Stage 3 output back into the shipped AnalystRun surface."""
    source_to_evidence_ids: dict[str, list[str]] = defaultdict(list)
    for item in bundle.evidence:
        source_to_evidence_ids[item.source_id].append(item.id)

    raw_claims: list[RawClaim] = []
    for idx, claim in enumerate(analysis.claims, start=1):
        evidence_ids = _ordered_unique(
            evidence_id
            for source_id in claim.source_references
            for evidence_id in source_to_evidence_ids.get(source_id, [])[:2]
        )
        raw_claims.append(
            RawClaim(
                id=f"RC-{idx}",
                statement=claim.statement,
                evidence_ids=evidence_ids,
                confidence=str(claim.confidence.value).lower(),
                reasoning=analysis.reasoning,
            )
        )

    supporting_claim_ids = [claim.id for claim in raw_claims]
    supporting_evidence_ids = _ordered_unique(
        evidence_id
        for claim in raw_claims
        for evidence_id in claim.evidence_ids
    )

    return AnalystRun(
        analyst_label=analyst_label,
        model=model_name,
        frame=analysis.reasoning_frame,
        claims=raw_claims,
        assumptions=[
            RuntimeAssumption(
                id=assumption.id,
                statement=assumption.statement,
                basis=assumption.if_wrong_impact,
            )
            for assumption in analysis.assumptions
        ],
        recommendations=[
            Recommendation(
                statement=analysis.recommendation,
                supporting_claim_ids=supporting_claim_ids,
                conditions="; ".join(analysis.falsification_conditions),
            )
        ],
        counterarguments=[
            RuntimeCounterargument(
                target=analysis.recommendation,
                argument=analysis.counter_argument.argument,
                evidence_ids=supporting_evidence_ids[:3],
            )
        ],
        summary=analysis.reasoning,
    )


def build_tyler_alias_mapping(analyst_runs: list[AnalystRun]) -> dict[str, str]:
    """Assign deterministic Tyler aliases A/B/C to successful analyst runs."""
    aliases = ["A", "B", "C"]
    succeeded = [run for run in analyst_runs if run.succeeded]
    mapping: dict[str, str] = {}
    for idx, run in enumerate(succeeded):
        mapping[run.analyst_label] = aliases[idx] if idx < len(aliases) else f"A{idx + 1}"
    return mapping


def _ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered


def _normalize_statement_key(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


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


def tyler_stage4_to_current_ledger(
    result: ClaimExtractionResult,
    stage_3_results: list[AnalysisObject],
    bundle: EvidenceBundle,
    alias_mapping: dict[str, str],
) -> ClaimLedger:
    """Project Tyler Stage 4 output back into the shipped ClaimLedger contract."""
    reverse_alias_mapping = {alias: label for label, alias in alias_mapping.items()}
    source_to_evidence_ids: dict[str, list[str]] = defaultdict(list)
    for item in bundle.evidence:
        source_to_evidence_ids[item.source_id].append(item.id)

    raw_claim_records: list[tuple[str, str, str, set[str], set[str]]] = []
    for analysis in stage_3_results:
        alias = analysis.model_alias
        for claim in analysis.claims:
            source_refs = set(claim.source_references)
            tokens = set(_normalize_statement_key(claim.statement).split())
            raw_claim_records.append(
                (f"{alias}:{claim.id}", alias, claim.statement, source_refs, tokens)
            )

    def _match_raw_claim_ids(entry: ClaimLedgerEntry) -> list[str]:
        entry_tokens = set(_normalize_statement_key(entry.statement).split())
        entry_source_refs = set(entry.source_references)
        candidates: list[tuple[int, str]] = []
        for raw_id, alias, statement, source_refs, tokens in raw_claim_records:
            if alias not in entry.source_models:
                continue
            score = 0
            if entry_source_refs & source_refs:
                score += 4
            score += len(entry_tokens & tokens)
            if score > 0:
                candidates.append((score, raw_id))
        if not candidates:
            fallback = [
                raw_id
                for raw_id, alias, _statement, _source_refs, _tokens in raw_claim_records
                if alias in entry.source_models
            ]
            return _ordered_unique(fallback[:1])
        candidates.sort(reverse=True)
        return _ordered_unique([raw_id for _score, raw_id in candidates[:4]])

    current_claims: list[RuntimeClaim] = []
    for entry in result.claim_ledger:
        source_raw_claim_ids = _match_raw_claim_ids(entry)
        evidence_ids = _ordered_unique(
            [
                evidence_id
                for source_id in entry.source_references
                for evidence_id in source_to_evidence_ids.get(source_id, [])
            ]
        )
        current_status = {
            ClaimStatus.SUPPORTED: "supported",
            ClaimStatus.VERIFIED: "supported",
            ClaimStatus.REFUTED: "refuted",
        }.get(entry.status, "initial")
        current_claims.append(
            RuntimeClaim(
                id=entry.id,
                statement=entry.statement,
                status=current_status,
                source_raw_claim_ids=source_raw_claim_ids or [f"derived:{entry.id}"],
                analyst_sources=[
                    reverse_alias_mapping[alias]
                    for alias in entry.source_models
                    if alias in reverse_alias_mapping
                ],
                evidence_ids=evidence_ids,
                confidence="medium",
                status_reason=f"Projected from Tyler Stage 4 status {entry.status.value}.",
            )
        )

    current_disputes: list[RuntimeDispute] = []
    for dispute in result.dispute_queue:
        if len(dispute.claims_involved) < 2:
            _LOG.warning(
                "Skipping Tyler Stage 4 dispute %s in current-ledger projection because it references fewer than 2 claims: %s",
                dispute.id,
                dispute.claims_involved,
            )
            continue
        current_type = {
            DisputeType.EMPIRICAL: "factual_conflict",
            DisputeType.INTERPRETIVE: "interpretive_conflict",
            DisputeType.PREFERENCE_WEIGHTED: "preference_conflict",
            DisputeType.SPEC_AMBIGUITY: "ambiguity",
            DisputeType.OTHER: "ambiguity",
        }[dispute.type]
        current_route = {
            "stage_5_evidence": "verify",
            "stage_5_arbitration": "arbitrate",
            "stage_6_user_input": "surface",
            "logged_only": "surface",
        }[dispute.resolution_routing]
        current_disputes.append(
            RuntimeDispute(
                id=dispute.id,
                dispute_type=current_type,
                route=current_route,
                claim_ids=dispute.claims_involved,
                description=dispute.description,
                severity="decision_critical" if dispute.decision_critical else "notable",
                resolved=dispute.status is not DisputeStatus.UNRESOLVED,
                resolution_summary=dispute.decision_critical_rationale,
            )
        )

    return ClaimLedger(
        claims=current_claims,
        disputes=current_disputes,
        arbitration_results=[],
    )


def _tyler_claim_status_to_current(status: ClaimStatus) -> str:
    """Project Tyler claim lifecycle states onto the shipped runtime statuses."""
    return {
        ClaimStatus.SUPPORTED: "supported",
        ClaimStatus.VERIFIED: "supported",
        ClaimStatus.REFUTED: "refuted",
        ClaimStatus.UNRESOLVED: "inconclusive",
    }.get(status, "initial")


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


def tyler_stage5_to_current_ledger(
    verification_result: VerificationResult,
    prior_ledger: ClaimLedger,
) -> ClaimLedger:
    """Project Tyler Stage 5 output into the shipped ClaimLedger contract."""
    claim_map = {claim.id: claim.model_copy(deep=True) for claim in prior_ledger.claims}
    for updated_claim in verification_result.updated_claim_ledger:
        current_claim = claim_map.get(updated_claim.id)
        if current_claim is None:
            continue
        current_claim.status = _tyler_claim_status_to_current(updated_claim.status)
        current_claim.status_reason = f"Projected from Tyler Stage 5 status {updated_claim.status.value}."
        claim_map[current_claim.id] = current_claim

    dispute_map = {dispute.id: dispute.model_copy(deep=True) for dispute in prior_ledger.disputes}
    for updated_dispute in verification_result.updated_dispute_queue:
        current_dispute = dispute_map.get(updated_dispute.id)
        if current_dispute is None:
            continue
        current_dispute.resolved = updated_dispute.status in {DisputeStatus.RESOLVED, DisputeStatus.DEFERRED_TO_USER}
        current_dispute.resolution_summary = updated_dispute.decision_critical_rationale
        dispute_map[current_dispute.id] = current_dispute

    arbitration_results = [
        tyler_assessment_to_current_arbitration(
            assessment,
            verification_result.additional_sources,
        )
        for assessment in verification_result.disputes_investigated
    ]

    return ClaimLedger(
        claims=list(claim_map.values()),
        disputes=list(dispute_map.values()),
        arbitration_results=arbitration_results,
    )


def tyler_synthesis_to_current_report(report: SynthesisReport, original_query: str) -> FinalReport:
    """Project Tyler Stage 6 output into the shipped structured report surface."""
    cited_claim_ids = [entry.claim_id for entry in report.claim_ledger_excerpt]
    disagreement_summary = "\n".join(
        f"{entry.dispute_id}: {entry.summary} — {entry.resolution}"
        for entry in report.disagreement_map
    )
    alternatives = [
        f"{alternative.alternative} — {alternative.conditions_for_preference}"
        for alternative in report.preserved_alternatives
    ]
    return FinalReport(
        title=original_query[:120] or "Grounded research report",
        question=original_query,
        recommendation=report.executive_recommendation,
        alternatives=alternatives,
        disagreement_summary=disagreement_summary,
        evidence_gaps=report.evidence_gaps,
        flip_conditions=report.conditions_of_validity,
        cited_claim_ids=cited_claim_ids,
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
