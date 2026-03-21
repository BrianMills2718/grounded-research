"""Claim canonicalization: extraction, deduplication, ledger assembly, dispute detection.

Phases 3a through 3c of the adjudication pipeline. Takes analyst runs and
produces the canonical ClaimLedger with disputes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from grounded_research.config import get_model
from grounded_research.models import (
    AnalystRun,
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

def extract_raw_claims(analyst_runs: list[AnalystRun]) -> tuple[list[RawClaim], dict[str, str]]:
    """Gather all raw claims from analyst runs with provenance tracking.

    Returns (flat list of all RawClaims, mapping of claim_id → analyst_label).
    Simple extraction — no LLM needed. Add normalization pass only if dedup
    suffers from phrasing variance.
    """
    all_claims: list[RawClaim] = []
    claim_to_analyst: dict[str, str] = {}

    for run in analyst_runs:
        if not run.succeeded:
            continue
        for claim in run.claims:
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
        canonical_statement: str = Field(description="The merged canonical claim text.")
        raw_claim_ids: list[str] = Field(description="IDs of raw claims in this group.")
        confidence: str = Field(description="high, medium, or low")

    class DeduplicationResult(BaseModel):
        """LLM output: grouped equivalence classes of claims."""
        groups: list[ClaimGroup]

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "dedup.yaml"),
        raw_claims=[c.model_dump() for c in raw_claims],
    )

    model = get_model("deduplication")
    result, _meta = await acall_llm_structured(
        model,
        messages,
        response_model=DeduplicationResult,
        task="claim_deduplication",
        trace_id=f"{trace_id}/dedup",
        max_budget=max_budget,
    )

    # Build canonical claims from groups
    raw_claim_map = {c.id: c for c in raw_claims}
    canonical_claims: list[Claim] = []

    for group in result.groups:
        # Merge provenance from all raw claims in the group
        source_ids = group.raw_claim_ids
        analyst_sources = list({
            claim_to_analyst[rid] for rid in source_ids if rid in claim_to_analyst
        })
        evidence_ids: list[str] = []
        for rid in source_ids:
            if rid in raw_claim_map:
                evidence_ids.extend(raw_claim_map[rid].evidence_ids)
        evidence_ids = list(dict.fromkeys(evidence_ids))  # deduplicate preserving order

        canonical_claims.append(Claim(
            statement=group.canonical_statement,
            source_raw_claim_ids=source_ids,
            analyst_sources=analyst_sources,
            evidence_ids=evidence_ids,
            confidence=group.confidence if group.confidence in ("high", "medium", "low") else "medium",
        ))

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
        claim_ids: list[str] = Field(description="IDs of claims in conflict.")
        dispute_type: str = Field(description="factual_conflict, interpretive_conflict, preference_conflict, or ambiguity")
        description: str = Field(description="Human-readable description of the conflict.")
        severity: str = Field(description="decision_critical, notable, or minor")

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
