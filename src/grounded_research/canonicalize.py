"""Claim canonicalization: extraction, deduplication, ledger assembly, dispute detection.

Phases 3a through 3c of the adjudication pipeline. Takes analyst runs and
produces the canonical ClaimLedger with disputes.
"""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from pathlib import Path
import re
from typing import Any

from grounded_research.config import (
    get_dedup_config,
    get_fallback_models,
    get_model,
    get_phase_concurrency_config,
    get_tyler_literal_parity_config,
)
from grounded_research.models import (
    AnalystRun,
    EvidenceBundle,
    ArbitrationResult,
    Claim,
    ClaimLedger,
    Dispute,
    QuestionDecomposition,
    RawClaim,
    DISPUTE_ROUTING,
)
from grounded_research.tyler_v1_adapters import (
    build_tyler_alias_mapping,
    current_analyst_run_to_tyler_analysis,
    current_decomposition_to_tyler,
    normalize_tyler_claim_extraction_result,
    tyler_stage4_to_current_ledger,
)
from grounded_research.tyler_v1_models import (
    ClaimExtractionResult as TylerClaimExtractionResult,
    DecompositionResult as TylerDecompositionResult,
)
from grounded_research.runtime_policy import get_request_timeout

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Tyler Stage 4 migration path
# ---------------------------------------------------------------------------

def _current_frame_to_tyler(frame: str) -> str:
    """Map the shipped analyst frame names onto Tyler's Stage 3 contract."""
    if frame in {"step_back_abstraction", "structured_decomposition", "verification_first"}:
        return frame
    return "verification_first"


def _tyler_stage4_assertion_count(stage_3_results: list["AnalysisObject"]) -> int:
    """Count extractable Stage 3 assertions before Stage 4 runs.

    A schema-valid empty Stage 4 result is only acceptable when the upstream
    Tyler analyses are themselves empty. When analysts produced claims or
    assumptions, Stage 4 must not silently collapse to an empty ledger.
    """
    return sum(len(result.claims) + len(result.assumptions) for result in stage_3_results)


def _summarize_stage4_exception(exc: Exception) -> str:
    """Summarize Stage 4 schema/runtime failures for a corrective retry prompt."""
    lines = [line.strip() for line in str(exc).splitlines() if line.strip()]
    return " | ".join(lines[:8])[:1200]


async def _get_tyler_stage1_result(
    *,
    decomposition: QuestionDecomposition | None,
    original_query: str,
    trace_id: str,
    max_budget: float,
) -> TylerDecompositionResult:
    """Produce a Tyler-native Stage 1 artifact for Stage 4 prompt rendering."""
    if decomposition is not None:
        return current_decomposition_to_tyler(decomposition, original_query=original_query)

    from grounded_research.decompose import decompose_question_tyler_v1

    return await decompose_question_tyler_v1(
        question=original_query,
        trace_id=trace_id,
        max_budget=max_budget,
    )


async def canonicalize_tyler_v1(
    analyst_runs: list[AnalystRun],
    bundle: EvidenceBundle,
    *,
    decomposition: QuestionDecomposition | None,
    tyler_stage_1_result: TylerDecompositionResult | None = None,
    tyler_stage_3_results: list["AnalysisObject"] | None = None,
    trace_id: str,
    max_budget: float = 1.0,
) -> tuple[TylerClaimExtractionResult, ClaimLedger]:
    """Run Tyler's literal Stage 4 contract and project it to the current ledger.

    This is the primary migration path for the Stage 4 refactor. The Tyler
    artifact is treated as the source of truth; the current ClaimLedger is an
    explicit projection kept only so Stage 5 and Stage 6 can continue running
    until their own migrations land.
    """
    from llm_client import acall_llm_structured, render_prompt

    successful_runs = [run for run in analyst_runs if run.succeeded]
    if len(successful_runs) < 2:
        raise ValueError("Tyler Stage 4 requires at least 2 successful analyst runs.")

    original_query = bundle.question.text if bundle.question else ""
    tyler_stage1 = tyler_stage_1_result or await _get_tyler_stage1_result(
        decomposition=decomposition,
        original_query=original_query,
        trace_id=f"{trace_id}/stage1_adapter",
        max_budget=max_budget * 0.15,
    )
    alias_mapping = build_tyler_alias_mapping(successful_runs)
    if tyler_stage_3_results is None:
        tyler_stage3_results = [
            current_analyst_run_to_tyler_analysis(
                run=run,
                bundle=bundle,
                model_alias=alias_mapping[run.analyst_label],
                reasoning_frame=_current_frame_to_tyler(run.frame),
            )
            for run in successful_runs
        ]
    else:
        tyler_stage3_results = list(tyler_stage_3_results)
    stage4_input_assertions = _tyler_stage4_assertion_count(tyler_stage3_results)

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "tyler_v1_stage4.yaml"),
        original_query=original_query,
        stage_1=tyler_stage1.model_dump(mode="json"),
        stage_3_results=[analysis.model_dump(mode="json") for analysis in tyler_stage3_results],
        response_schema_json=TylerClaimExtractionResult.model_json_schema(),
    )
    parity_policy = get_tyler_literal_parity_config()

    async def _run_stage4_retry(issue_summary: str) -> TylerClaimExtractionResult:
        retry_messages = list(messages)
        retry_messages.append(
            {
                "role": "user",
                "content": (
                    "Correction for Tyler Stage 4: the previous response was not acceptable. "
                    f"Issue: {issue_summary} "
                    "Retry now. Keep the exact same schema, but place only assumptions in "
                    "`assumption_set`, place all disputes in `dispute_queue`, populate "
                    "`statistics.claims_per_model`, and do not return an empty claim ledger "
                    "when the analyses contain extractable assertions."
                ),
            }
        )
        retry_model = str(parity_policy.get("stage4_retry_model") or get_model("claim_extraction"))
        retry_fallback_models = parity_policy.get("stage4_retry_fallback_models")
        retry_result, _retry_meta = await acall_llm_structured(
            retry_model,
            retry_messages,
            response_model=TylerClaimExtractionResult,
            task="claim_extraction_tyler_v1_retry",
            trace_id=f"{trace_id}/claim_extraction_tyler_v1_retry",
            timeout=get_request_timeout("claim_extraction"),
            max_budget=max_budget,
            fallback_models=retry_fallback_models if retry_fallback_models else get_fallback_models("claim_extraction"),
        )
        return retry_result

    try:
        result, _meta = await acall_llm_structured(
            get_model("claim_extraction"),
            messages,
            response_model=TylerClaimExtractionResult,
            task="claim_extraction_tyler_v1",
            trace_id=f"{trace_id}/claim_extraction_tyler_v1",
            timeout=get_request_timeout("claim_extraction"),
            max_budget=max_budget,
            fallback_models=get_fallback_models("claim_extraction"),
        )
    except Exception as exc:
        if not bool(parity_policy.get("stage4_retry_on_empty_claims", True)) or stage4_input_assertions <= 0:
            raise
        result = await _run_stage4_retry(
            f"schema or validation failure from the primary Stage 4 call: {_summarize_stage4_exception(exc)}"
        )

    normalized = normalize_tyler_claim_extraction_result(
        result,
        valid_source_ids={source.id for source in bundle.sources},
        allowed_model_aliases=set(alias_mapping.values()),
    )
    should_retry_empty_stage4 = (
        bool(parity_policy.get("stage4_retry_on_empty_claims", True))
        and stage4_input_assertions > 0
        and not normalized.claim_ledger
        and not normalized.assumption_set
    )
    if should_retry_empty_stage4:
        retry_result = await _run_stage4_retry(
            "the previous Stage 4 result extracted zero claims and zero assumptions "
            f"from analyses containing {stage4_input_assertions} upstream claims/assumptions."
        )
        normalized = normalize_tyler_claim_extraction_result(
            retry_result,
            valid_source_ids={source.id for source in bundle.sources},
            allowed_model_aliases=set(alias_mapping.values()),
        )
        if not normalized.claim_ledger and not normalized.assumption_set:
            raise ValueError(
                "Tyler Stage 4 returned an empty claim ledger and assumption set "
                f"after retry despite {stage4_input_assertions} upstream assertions."
            )
    ledger = tyler_stage4_to_current_ledger(
        normalized,
        analyst_runs=successful_runs,
        bundle=bundle,
        alias_mapping=alias_mapping,
    )
    return normalized, ledger


# ---------------------------------------------------------------------------
# Legacy Phase 3a: Claim extraction
# ---------------------------------------------------------------------------

async def extract_raw_claims(
    analyst_runs: list[AnalystRun],
    bundle: EvidenceBundle,
    trace_id: str,
    max_budget: float = 1.0,
) -> tuple[list[RawClaim], dict[str, str]]:
    """Extract normalized raw claims from analyst outputs with provenance tracking.

    This is a dedicated claim-extraction stage rather than simple copy-through.
    Each successful analyst run is processed independently so compound or vague
    claims can be split and normalized into self-contained ledger-ready claims.

    Returns (flat list of all RawClaims, mapping of claim_id → analyst_label).
    """
    from llm_client import acall_llm_structured, render_prompt
    from pydantic import BaseModel, Field
    from typing import Literal

    import logging

    logger = logging.getLogger(__name__)
    valid_evidence_ids = {e.id for e in bundle.evidence}
    evidence_by_id = {e.id: e for e in bundle.evidence}
    source_by_id = {s.id: s for s in bundle.sources}

    all_claims: list[RawClaim] = []
    claim_to_analyst: dict[str, str] = {}

    successful_runs = [run for run in analyst_runs if run.succeeded]
    if not successful_runs:
        return all_claims, claim_to_analyst

    phase_concurrency = get_phase_concurrency_config()
    claim_extraction_max_concurrency = max(
        1,
        int(phase_concurrency.get("claim_extraction_max_concurrency", 1)),
    )
    extraction_semaphore = asyncio.Semaphore(claim_extraction_max_concurrency)

    async def _extract_for_run(run: AnalystRun) -> tuple[AnalystRun, BaseModel]:
        async with extraction_semaphore:
            cited_evidence_ids = {
                eid
                for claim in run.claims
                for eid in claim.evidence_ids
                if eid in valid_evidence_ids
            }
            cited_evidence_ids.update(
                eid
                for counterargument in run.counterarguments
                for eid in counterargument.evidence_ids
                if eid in valid_evidence_ids
            )

            if not cited_evidence_ids:
                logger.warning(
                    "Claim extraction %s: no valid cited evidence IDs available; skipping extraction",
                    run.analyst_label,
                )

                class EmptyClaimExtractionResult(BaseModel):
                    """No-op extraction result when there is no valid candidate evidence."""

                    claims: list[RawClaim] = Field(default_factory=list)

                return run, EmptyClaimExtractionResult()

            relevant_evidence = [evidence_by_id[eid].model_dump() for eid in cited_evidence_ids]
            relevant_sources = [
                source_by_id[e.source_id].model_dump(mode="json")
                for e in (evidence_by_id[eid] for eid in cited_evidence_ids)
                if e.source_id in source_by_id
            ]
            ordered_candidate_ids = sorted(cited_evidence_ids)
            AllowedEvidenceId = Literal.__getitem__(tuple(ordered_candidate_ids))

            class ExtractedRawClaim(BaseModel):
                """LLM-facing atomic claim without system-assigned IDs."""

                statement: str = Field(
                    description=(
                        "A self-contained, falsifiable claim rewritten from the analyst's "
                        "input claims. Preserve concrete entities, dates, numbers, and "
                        "benchmarks when available."
                    ),
                )
                evidence_ids: list[AllowedEvidenceId] = Field(
                    default_factory=list,
                    description=(
                        "One or more supporting evidence IDs chosen only from the "
                        f"candidate set: {ordered_candidate_ids}. Do not emit source IDs "
                        "or invented evidence IDs."
                    ),
                )
                confidence: str = Field(description="high, medium, or low")
                reasoning: str = Field(
                    default="",
                    description="Why this atomic claim was extracted and how it maps back to the analyst's input.",
                )

            class ClaimExtractionResult(BaseModel):
                """LLM output for one analyst's claim extraction pass."""

                claims: list[ExtractedRawClaim] = Field(
                    default_factory=list,
                    description=(
                        "Atomic normalized claims extracted from the analyst's structured "
                        "output. Omit any claim that cannot be grounded in the candidate "
                        "evidence IDs."
                    ),
                )

            messages = render_prompt(
                str(_PROJECT_ROOT / "prompts" / "claimify.yaml"),
                analyst_label=run.analyst_label,
                analyst_summary=run.summary,
                analyst_claims=[claim.model_dump() for claim in run.claims],
                assumptions=[assumption.model_dump() for assumption in run.assumptions],
                recommendations=[recommendation.model_dump() for recommendation in run.recommendations],
                counterarguments=[counterargument.model_dump() for counterargument in run.counterarguments],
                evidence=relevant_evidence,
                source_records=relevant_sources,
                valid_evidence_ids=ordered_candidate_ids,
            )

            result, _meta = await acall_llm_structured(
                get_model("claim_extraction"),
                messages,
                response_model=ClaimExtractionResult,
                task="claim_extraction",
                trace_id=f"{trace_id}/claim_extract/{run.analyst_label}",
                timeout=get_request_timeout("claim_extraction"),
                max_budget=max_budget / len(successful_runs),
                fallback_models=get_fallback_models("claim_extraction"),
            )
            return run, result

    extraction_results = await asyncio.gather(*[_extract_for_run(run) for run in successful_runs])

    for run, extraction in extraction_results:
        for extracted in extraction.claims:
            invalid = [eid for eid in extracted.evidence_ids if eid not in valid_evidence_ids]
            if invalid:
                logger.warning(
                    "Claim extraction %s: stripping hallucinated evidence IDs %s",
                    run.analyst_label,
                    invalid,
                )
            cleaned_ids = [eid for eid in extracted.evidence_ids if eid in valid_evidence_ids]
            if not cleaned_ids:
                logger.warning(
                    "Claim extraction %s: dropping ungrounded claim after evidence cleanup: %s",
                    run.analyst_label,
                    extracted.statement[:160],
                )
                continue
            claim = RawClaim(
                statement=extracted.statement,
                evidence_ids=cleaned_ids,
                confidence=extracted.confidence if extracted.confidence in {"high", "medium", "low"} else "medium",
                reasoning=extracted.reasoning,
            )
            all_claims.append(claim)
            claim_to_analyst[claim.id] = run.analyst_label

    return all_claims, claim_to_analyst


# ---------------------------------------------------------------------------
# Phase 3b: Semantic deduplication
# ---------------------------------------------------------------------------

async def deduplicate_claims(
    raw_claims: list[RawClaim],
    claim_to_analyst: dict[str, str],
    trace_id: str,
    max_budget: float = 1.0,
) -> list[Claim]:
    """Deduplicate raw claims into canonical claims via LLM grouping.

    The LLM receives all raw claims and groups them into equivalence classes.
    Each group becomes one canonical Claim with merged provenance.
    """
    from llm_client import acall_llm_structured, render_prompt
    from pydantic import BaseModel, Field

    class ClaimGroup(BaseModel):
        """One equivalence class of raw claims."""
        canonical_statement: str = Field(description="The merged canonical claim text that captures the shared meaning of the grouped claims.")
        raw_claim_ids: list[str] = Field(
            description="IDs (RC-xxx format) of the raw claims in this group. Every raw claim must appear in exactly one group.",
            min_length=1,
        )
        confidence: str = Field(description="high, medium, or low")

    class DeduplicationResult(BaseModel):
        """LLM output: grouped equivalence classes of claims. Every raw claim must be in exactly one group."""
        groups: list[ClaimGroup] = Field(
            description="Equivalence classes of claims. Must contain at least one group. Every raw claim ID from the input must appear in exactly one group.",
            min_length=1,
        )

    # Build canonical claims from groups
    import logging
    logger = logging.getLogger(__name__)
    dedup_cfg = get_dedup_config()
    staged_trigger_claims = int(dedup_cfg["staged_trigger_claims"])
    bucket_max_claims = int(dedup_cfg["bucket_max_claims"])
    max_doc_frequency_ratio = float(dedup_cfg["max_doc_frequency_ratio"])
    min_shared_informative_tokens = int(dedup_cfg["min_shared_informative_tokens"])

    raw_claim_map = {c.id: c for c in raw_claims}
    total_claims = len(raw_claims)

    if not raw_claims:
        return []

    def _promote_raw_claims(
        claims_subset: list[RawClaim],
        *,
        log_warning: bool,
    ) -> list[Claim]:
        if log_warning:
            logger.warning(
                "Dedup output invalid after retry for %d raw claims — promoting raw claims 1:1",
                len(claims_subset),
            )
        return [
            Claim(
                statement=rc.statement,
                source_raw_claim_ids=[rc.id],
                analyst_sources=[claim_to_analyst.get(rc.id, "unknown")],
                evidence_ids=rc.evidence_ids,
                confidence=rc.confidence,
            )
            for rc in claims_subset
        ]

    def _build_claims(groups: list[ClaimGroup]) -> list[Claim]:
        canonical_claims: list[Claim] = []
        for group in groups:
            source_ids = group.raw_claim_ids
            analyst_sources = list({
                claim_to_analyst[rid] for rid in source_ids if rid in claim_to_analyst
            })
            evidence_ids: list[str] = []
            for rid in source_ids:
                if rid in raw_claim_map:
                    evidence_ids.extend(raw_claim_map[rid].evidence_ids)
            evidence_ids = list(dict.fromkeys(evidence_ids))

            canonical_claims.append(Claim(
                statement=group.canonical_statement,
                source_raw_claim_ids=source_ids,
                analyst_sources=analyst_sources,
                evidence_ids=evidence_ids,
                confidence=group.confidence if group.confidence in ("high", "medium", "low") else "medium",
            ))
        return canonical_claims

    def _validate_groups(groups: list[ClaimGroup], allowed_claim_ids: set[str]) -> list[str]:
        errors: list[str] = []
        if not groups:
            errors.append("Dedup returned zero groups.")
            return errors

        seen: list[str] = []
        unknown_ids: list[str] = []
        for idx, group in enumerate(groups, start=1):
            if not group.raw_claim_ids:
                errors.append(f"Group {idx} is empty.")
                continue
            for rid in group.raw_claim_ids:
                if rid not in allowed_claim_ids:
                    unknown_ids.append(rid)
                else:
                    seen.append(rid)

        if unknown_ids:
            errors.append(f"Unknown raw claim IDs referenced: {sorted(set(unknown_ids))}")

        duplicates = sorted({rid for rid in seen if seen.count(rid) > 1})
        if duplicates:
            errors.append(f"Duplicate raw claim IDs across groups: {duplicates}")

        missing = sorted(allowed_claim_ids - set(seen))
        if missing:
            errors.append(f"Missing raw claim IDs from groups: {missing}")

        return errors

    async def _call_dedup(messages: list[dict[str, str]], call_trace_id: str, call_budget: float) -> DeduplicationResult:
        result, _meta = await acall_llm_structured(
            get_model("deduplication"),
            messages,
            response_model=DeduplicationResult,
            task="claim_deduplication",
            trace_id=call_trace_id,
            timeout=get_request_timeout("deduplication"),
            max_budget=call_budget,
            fallback_models=get_fallback_models("deduplication"),
        )
        return result

    stopwords = {
        "about", "across", "after", "against", "among", "because", "between",
        "claim", "claims", "current", "different", "during", "effect",
        "effects", "evidence", "finding", "findings", "impact", "impacts",
        "include", "includes", "many", "participants", "pilot", "pilots",
        "program", "programs", "reported", "results", "show", "shows",
        "showed", "study", "studies", "their", "there", "these", "they",
        "this", "through", "universal", "basic", "income", "employment",
        "workforce", "participation", "labor", "market", "markets", "workers",
        "the", "for", "into", "from", "with", "without", "that", "than",
        "work", "works", "worked", "working", "increase", "increased",
        "improved", "found", "experiment", "experiments", "trial", "trials",
    }

    def _claim_tokens(statement: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}", statement.lower())
            if token not in stopwords
        }

    def _token_family(token: str) -> str:
        if len(token) >= 6:
            return token[:5]
        return token

    raw_tokens = {claim.id: _claim_tokens(claim.statement) for claim in raw_claims}
    token_doc_freq = Counter(
        token
        for tokens in raw_tokens.values()
        for token in tokens
    )

    informative_tokens = {
        claim.id: {
            token
            for token in raw_tokens[claim.id]
            if token_doc_freq[token] / total_claims <= max_doc_frequency_ratio
        }
        for claim in raw_claims
    }
    informative_token_families = {
        claim.id: {_token_family(token) for token in informative_tokens[claim.id]}
        for claim in raw_claims
    }

    def _claims_should_share_bucket(left: RawClaim, right: RawClaim) -> bool:
        if set(left.evidence_ids) & set(right.evidence_ids):
            return True
        shared_tokens = informative_tokens[left.id] & informative_tokens[right.id]
        if len(shared_tokens) >= min_shared_informative_tokens:
            return True
        shared_families = (
            informative_token_families[left.id]
            & informative_token_families[right.id]
        )
        return len(shared_families) >= min_shared_informative_tokens

    def _claim_similarity_score(left: RawClaim, right: RawClaim) -> tuple[int, int, int]:
        """Rank local claim similarity for staged bucket construction.

        Shared evidence is the strongest signal because claims grounded in the
        same evidence should be considered together before the LLM is asked to
        merge or keep them separate.
        """
        shared_evidence = len(set(left.evidence_ids) & set(right.evidence_ids))
        shared_tokens = len(informative_tokens[left.id] & informative_tokens[right.id])
        shared_families = len(
            informative_token_families[left.id]
            & informative_token_families[right.id]
        )
        return (shared_evidence, shared_tokens, shared_families)

    def _split_large_component(component: list[RawClaim]) -> list[list[RawClaim]]:
        similarity_scores: dict[str, dict[str, tuple[int, int, int]]] = defaultdict(dict)
        for idx, left in enumerate(component):
            for right in component[idx + 1:]:
                score = _claim_similarity_score(left, right)
                similarity_scores[left.id][right.id] = score
                similarity_scores[right.id][left.id] = score

        remaining = {claim.id: claim for claim in component}
        staged_buckets: list[list[RawClaim]] = []

        while remaining:
            seed_id = max(
                remaining,
                key=lambda claim_id: (
                    sum(similarity_scores[claim_id].get(other_id, (0, 0, 0))[0] for other_id in remaining if other_id != claim_id),
                    sum(similarity_scores[claim_id].get(other_id, (0, 0, 0))[1] for other_id in remaining if other_id != claim_id),
                    sum(similarity_scores[claim_id].get(other_id, (0, 0, 0))[2] for other_id in remaining if other_id != claim_id),
                    len(informative_tokens[claim_id]),
                    claim_id,
                ),
            )
            bucket_ids = [seed_id]
            remaining.pop(seed_id)

            while remaining and len(bucket_ids) < bucket_max_claims:
                best_id: str | None = None
                best_key: tuple[tuple[int, int, int], tuple[int, int, int], int, str] | None = None
                for candidate_id in remaining:
                    pair_scores = [
                        similarity_scores[candidate_id].get(bucket_id, (0, 0, 0))
                        for bucket_id in bucket_ids
                    ]
                    max_pair_score = max(pair_scores, default=(0, 0, 0))
                    total_pair_score = (
                        sum(score[0] for score in pair_scores),
                        sum(score[1] for score in pair_scores),
                        sum(score[2] for score in pair_scores),
                    )
                    candidate_key = (
                        max_pair_score,
                        total_pair_score,
                        len(informative_tokens[candidate_id]),
                        candidate_id,
                    )
                    if best_key is None or candidate_key > best_key:
                        best_id = candidate_id
                        best_key = candidate_key

                if best_id is None or best_key is None or best_key[0] == (0, 0, 0):
                    break

                bucket_ids.append(best_id)
                remaining.pop(best_id)

            staged_buckets.append([raw_claim_map[claim_id] for claim_id in bucket_ids])

        return staged_buckets

    def _partition_raw_claims() -> list[list[RawClaim]]:
        if total_claims < staged_trigger_claims:
            return [raw_claims]

        claim_ids = [claim.id for claim in raw_claims]
        adjacency: dict[str, set[str]] = {claim_id: set() for claim_id in claim_ids}
        for idx, left in enumerate(raw_claims):
            for right in raw_claims[idx + 1:]:
                if _claims_should_share_bucket(left, right):
                    adjacency[left.id].add(right.id)
                    adjacency[right.id].add(left.id)

        components: list[list[RawClaim]] = []
        seen: set[str] = set()
        for claim in raw_claims:
            if claim.id in seen:
                continue
            queue = [claim.id]
            component_ids: list[str] = []
            while queue:
                current = queue.pop()
                if current in seen:
                    continue
                seen.add(current)
                component_ids.append(current)
                queue.extend(adjacency[current] - seen)

            component = [raw_claim_map[claim_id] for claim_id in component_ids]
            if len(component) <= bucket_max_claims:
                components.append(component)
            else:
                components.extend(_split_large_component(component))

        logger.info(
            "Staged dedup partitioned %d raw claims into %d bucket(s)",
            total_claims,
            len(components),
        )
        return components

    async def _dedup_bucket(
        claims_subset: list[RawClaim],
        bucket_index: int,
        call_budget: float,
    ) -> list[Claim]:
        if len(claims_subset) == 1:
            return _promote_raw_claims(claims_subset, log_warning=False)

        messages = render_prompt(
            str(_PROJECT_ROOT / "prompts" / "dedup.yaml"),
            raw_claims=[claim.model_dump() for claim in claims_subset],
        )
        allowed_claim_ids = {claim.id for claim in claims_subset}

        first_result = await _call_dedup(
            messages,
            f"{trace_id}/dedup/bucket_{bucket_index}",
            call_budget * 0.5,
        )
        validation_errors = _validate_groups(first_result.groups, allowed_claim_ids)
        if not validation_errors:
            return _build_claims(first_result.groups)

        logger.warning(
            "Dedup bucket %d attempt 1 invalid: %s",
            bucket_index,
            " | ".join(validation_errors),
        )
        retry_messages = messages + [
            {
                "role": "user",
                "content": (
                    "The previous grouping was structurally invalid. Fix it.\n"
                    f"Validation errors: {' | '.join(validation_errors)}\n"
                    "Return a corrected grouping where every raw claim ID appears exactly once, "
                    "no unknown IDs appear, and no group is empty."
                ),
            }
        ]
        retry_result = await _call_dedup(
            retry_messages,
            f"{trace_id}/dedup_retry/bucket_{bucket_index}",
            call_budget * 0.5,
        )
        retry_errors = _validate_groups(retry_result.groups, allowed_claim_ids)
        if retry_errors:
            logger.warning(
                "Dedup bucket %d retry invalid: %s",
                bucket_index,
                " | ".join(retry_errors),
            )
            return _promote_raw_claims(claims_subset, log_warning=True)

        return _build_claims(retry_result.groups)

    buckets = _partition_raw_claims()
    if len(buckets) == 1:
        return await _dedup_bucket(buckets[0], 1, max_budget)

    bucket_budget = max_budget / len(buckets)
    bucket_results = await asyncio.gather(*[
        _dedup_bucket(bucket, idx, bucket_budget)
        for idx, bucket in enumerate(buckets, start=1)
    ])
    canonical_claims = [claim for claims in bucket_results for claim in claims]
    logger.info(
        "Staged dedup produced %d canonical claims from %d raw claims across %d buckets",
        len(canonical_claims),
        total_claims,
        len(buckets),
    )
    return canonical_claims


# ---------------------------------------------------------------------------
# Phase 3c: Ledger assembly and dispute detection
# ---------------------------------------------------------------------------

async def detect_disputes(
    claims: list[Claim],
    trace_id: str,
    max_budget: float = 1.0,
) -> list[Dispute]:
    """Detect conflicts between canonical claims via LLM classification.

    The LLM identifies pairs/groups of claims in tension and assigns a
    DisputeType. Routing is code-owned via DISPUTE_ROUTING.
    """
    from llm_client import acall_llm_structured, render_prompt
    from pydantic import BaseModel, Field

    class RawDispute(BaseModel):
        """One conflict identified by the LLM."""
        claim_ids: list[str] = Field(description="IDs of claims in conflict (minimum 2).")
        dispute_type: str = Field(description="One of: factual_conflict, interpretive_conflict, preference_conflict, ambiguity")
        description: str = Field(description="Human-readable description of the conflict and why it matters.")
        severity: str = Field(
            description=(
                "One of: decision_critical, notable, minor. "
                "Use decision_critical when the claims directly contradict each other "
                "on a material point — a reader who believes Claim A would reach a "
                "different conclusion than one who believes Claim B. Most factual_conflict "
                "disputes should be decision_critical. Use notable only when both sides "
                "lead to broadly similar conclusions. Use minor for differences in "
                "emphasis or framing. When in doubt, prefer decision_critical."
            ),
        )

    class DisputeDetectionResult(BaseModel):
        """LLM output: detected conflicts between claims."""
        disputes: list[RawDispute]

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "dispute_classify.yaml"),
        claims=[c.model_dump() for c in claims],
    )

    model = get_model("dispute_classification")
    result, _meta = await acall_llm_structured(
        model,
        messages,
        response_model=DisputeDetectionResult,
        task="dispute_classification",
        trace_id=f"{trace_id}/disputes",
        timeout=get_request_timeout("dispute_classification"),
        max_budget=max_budget,
        fallback_models=get_fallback_models("dispute_classification"),
    )

    # Build typed disputes with code-owned routing
    claim_ids = {c.id for c in claims}
    disputes: list[Dispute] = []

    for raw in result.disputes:
        # Validate claim references
        valid_ids = [cid for cid in raw.claim_ids if cid in claim_ids]
        if len(valid_ids) < 2:
            continue  # Skip phantom disputes

        # Normalize dispute type
        dtype = raw.dispute_type if raw.dispute_type in DISPUTE_ROUTING else "ambiguity"
        route = DISPUTE_ROUTING[dtype]
        severity = raw.severity if raw.severity in ("decision_critical", "notable", "minor") else "notable"

        disputes.append(Dispute(
            dispute_type=dtype,
            route=route,
            claim_ids=valid_ids,
            description=raw.description,
            severity=severity,
        ))

    return disputes


def build_ledger(
    claims: list[Claim],
    disputes: list[Dispute],
) -> ClaimLedger:
    """Assemble the canonical ClaimLedger from claims and disputes."""
    return ClaimLedger(
        claims=claims,
        disputes=disputes,
        arbitration_results=[],
    )
