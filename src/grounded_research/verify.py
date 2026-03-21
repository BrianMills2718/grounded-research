"""Verification and arbitration for decision-critical disputes.

Phase 4: For each decision-critical dispute, searches for fresh evidence
and produces an ArbitrationResult. Uses llm_client's python_tools agent
loop for iterative search-and-reason behavior.

In v1, uses a simplified structured-call approach (Phase 4a/4b stepping
stone) rather than the full agentic loop. The agentic upgrade is planned
for when search tool infrastructure is wired.
"""

from __future__ import annotations

from pathlib import Path

from grounded_research.config import get_model
from grounded_research.models import (
    ArbitrationResult,
    Claim,
    ClaimLedger,
    Dispute,
    EvidenceBundle,
    EvidenceItem,
    VerificationQueryBatch,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


async def generate_verification_queries(
    disputes: list[Dispute],
    claims: list[Claim],
    trace_id: str,
    max_budget: float = 1.0,
) -> list[VerificationQueryBatch]:
    """Generate search queries for decision-critical disputes (Phase 4a).

    Returns one VerificationQueryBatch per dispute with targeted queries
    designed to find evidence that could resolve the conflict.
    """
    from llm_client import acall_llm_structured, render_prompt
    from pydantic import BaseModel, Field

    class QueryBatchResult(BaseModel):
        """LLM output: verification queries for disputes."""
        batches: list[VerificationQueryBatch]

    claim_map = {c.id: c for c in claims}
    dispute_context = []
    for d in disputes:
        relevant_claims = [claim_map[cid].model_dump() for cid in d.claim_ids if cid in claim_map]
        dispute_context.append({
            "dispute": d.model_dump(),
            "claims": relevant_claims,
        })

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "verification_queries.yaml"),
        disputes=dispute_context,
    )

    model = get_model("arbitration")
    result, _meta = await acall_llm_structured(
        model,
        messages,
        response_model=QueryBatchResult,
        task="verification_query_generation",
        trace_id=f"{trace_id}/queries",
        max_budget=max_budget,
    )

    return result.batches


async def arbitrate_dispute(
    dispute: Dispute,
    claims: list[Claim],
    bundle: EvidenceBundle,
    trace_id: str,
    max_budget: float = 1.0,
) -> ArbitrationResult:
    """Arbitrate a single dispute based on available evidence (Phase 4b).

    In v1, this uses the existing evidence bundle rather than fetching new
    evidence via search tools. The full agentic version with live search
    is the target design for post-v1.
    """
    from llm_client import acall_llm_structured, render_prompt

    claim_map = {c.id: c for c in claims}
    relevant_claims = [claim_map[cid] for cid in dispute.claim_ids if cid in claim_map]
    relevant_evidence_ids = set()
    for c in relevant_claims:
        relevant_evidence_ids.update(c.evidence_ids)
    relevant_evidence = [e for e in bundle.evidence if e.id in relevant_evidence_ids]

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "arbitration.yaml"),
        dispute=dispute.model_dump(),
        claims=[c.model_dump() for c in relevant_claims],
        evidence=[e.model_dump() for e in relevant_evidence],
    )

    model = get_model("arbitration")
    result, _meta = await acall_llm_structured(
        model,
        messages,
        response_model=ArbitrationResult,
        task="dispute_arbitration",
        trace_id=f"{trace_id}/arb/{dispute.id}",
        max_budget=max_budget,
    )

    result.dispute_id = dispute.id
    return result


async def verify_disputes(
    ledger: ClaimLedger,
    bundle: EvidenceBundle,
    trace_id: str,
    max_disputes: int = 5,
    max_budget: float = 2.0,
) -> tuple[ClaimLedger, list[ArbitrationResult]]:
    """Verify decision-critical disputes and update the ledger (Phase 4).

    Returns updated ledger and list of arbitration results.
    """
    import asyncio

    actionable = [
        d for d in ledger.disputes
        if d.severity == "decision_critical"
        and d.route in ("verify", "arbitrate")
        and not d.resolved
    ][:max_disputes]

    if not actionable:
        return ledger, []

    budget_per = max_budget / len(actionable)
    tasks = [
        arbitrate_dispute(d, ledger.claims, bundle, trace_id, budget_per)
        for d in actionable
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    arb_results: list[ArbitrationResult] = []
    for d, result in zip(actionable, results):
        if isinstance(result, Exception):
            continue
        arb_results.append(result)

        # Apply claim updates to ledger
        for claim_id, new_status in result.claim_updates.items():
            claim = ledger.claim_by_id(claim_id)
            if claim:
                claim.status = new_status
                claim.status_reason = f"Arbitration {result.id}: {result.verdict}"

        # Mark dispute resolved if verdict is not inconclusive
        if result.verdict != "inconclusive":
            d.resolved = True
            d.resolution_summary = result.reasoning[:200]

    ledger.arbitration_results = arb_results
    return ledger, arb_results
