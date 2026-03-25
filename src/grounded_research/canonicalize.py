"""Claim canonicalization: extraction, deduplication, ledger assembly, dispute detection.

Phases 3a through 3c of the adjudication pipeline. Takes analyst runs and
produces the canonical ClaimLedger with disputes.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from grounded_research.config import get_fallback_models, get_model
from grounded_research.models import (
    AnalystRun,
    EvidenceBundle,
    ArbitrationResult,
    Claim,
    ClaimLedger,
    Dispute,
    RawClaim,
    DISPUTE_ROUTING,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Phase 3a: Claim extraction
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

    async def _extract_for_run(run: AnalystRun) -> tuple[AnalystRun, BaseModel]:
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

    raw_claim_map = {c.id: c for c in raw_claims}

    def _fallback_promote() -> list[Claim]:
        logger.warning(
            "Dedup output invalid after retry for %d raw claims — promoting raw claims 1:1",
            len(raw_claims),
        )
        return [
            Claim(
                statement=rc.statement,
                source_raw_claim_ids=[rc.id],
                analyst_sources=[claim_to_analyst.get(rc.id, "unknown")],
                evidence_ids=rc.evidence_ids,
                confidence=rc.confidence,
            )
            for rc in raw_claims
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

    def _validate_groups(groups: list[ClaimGroup]) -> list[str]:
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
                if rid not in raw_claim_map:
                    unknown_ids.append(rid)
                else:
                    seen.append(rid)

        if unknown_ids:
            errors.append(f"Unknown raw claim IDs referenced: {sorted(set(unknown_ids))}")

        duplicates = sorted({rid for rid in seen if seen.count(rid) > 1})
        if duplicates:
            errors.append(f"Duplicate raw claim IDs across groups: {duplicates}")

        missing = sorted(set(raw_claim_map) - set(seen))
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
            max_budget=call_budget,
            fallback_models=get_fallback_models("deduplication"),
        )
        return result

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "dedup.yaml"),
        raw_claims=[c.model_dump() for c in raw_claims],
    )

    first_result = await _call_dedup(messages, f"{trace_id}/dedup", max_budget * 0.5)
    validation_errors = _validate_groups(first_result.groups)
    if not validation_errors:
        return _build_claims(first_result.groups)

    logger.warning("Dedup attempt 1 invalid: %s", " | ".join(validation_errors))
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
    retry_result = await _call_dedup(retry_messages, f"{trace_id}/dedup_retry", max_budget * 0.5)
    retry_errors = _validate_groups(retry_result.groups)
    if retry_errors:
        logger.warning("Dedup retry invalid: %s", " | ".join(retry_errors))
        return _fallback_promote()

    return _build_claims(retry_result.groups)


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
