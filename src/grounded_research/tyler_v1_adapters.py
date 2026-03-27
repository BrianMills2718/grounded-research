"""Adapters between the shipped runtime models and Tyler V1 literal contracts.

These adapters support the staged literal-parity migration. They make it
possible to generate Tyler-native artifacts without forcing the whole runtime
to switch contracts in one unsafe step.
"""

from __future__ import annotations

from collections import defaultdict

from grounded_research.models import AnalystRun, EvidenceBundle, QuestionDecomposition, SubQuestion, _make_id
from grounded_research.tyler_v1_models import (
    AnalysisObject,
    Assumption,
    ConfidenceLevel,
    CounterArgument,
    DecompositionResult,
    EvidenceLabel,
    EvidencePackage,
    Finding,
    Claim as TylerClaim,
    Source,
    SubQuestionEvidence,
)


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
            SubQuestion(
                id=_make_id("SQ-"),
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
) -> EvidencePackage:
    """Convert the current flat evidence bundle into Tyler's Stage 2 artifact."""
    current_sources = {source.id: source for source in bundle.sources}
    findings_by_subq_source: dict[tuple[str, str], list[Finding]] = defaultdict(list)

    tyler_question_ids = [sq.id for sq in decomposition.sub_questions]
    if not tyler_question_ids:
        raise ValueError("Tyler decomposition must include at least one sub-question.")

    for item in bundle.evidence:
        source = current_sources.get(item.source_id)
        if source is None:
            continue
        target_sub_questions = item.sub_question_ids or [tyler_question_ids[0]]
        for sub_question_id in target_sub_questions:
            findings_by_subq_source[(sub_question_id, source.id)].append(
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
