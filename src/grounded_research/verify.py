"""Verification and arbitration for decision-critical disputes.

Phase 4:
1) generate dispute-specific verification queries,
2) fetch fresh evidence by searching and reading,
3) append evidence to the active evidence bundle,
4) arbitrate disputes against the enriched evidence context.

This keeps the v1 pipeline in a structured flow (Phase 4a/4b), while enforcing
fail-loud invariants for evidence-backed arbitration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from grounded_research.config import get_budget, get_model, load_config
from grounded_research.models import (
    ArbitrationResult,
    Claim,
    ClaimLedger,
    Dispute,
    EvidenceBundle,
    EvidenceItem,
    SourceRecord,
    VerificationQueryBatch,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_FRESHNESS_MAP = {
    "time_sensitive": "pd",  # past day
    "mixed": "pm",          # past month
    "stable": "none",
}


@dataclass(frozen=True)
class VerificationWarning:
    """Typed warning payload for partial Phase-4 failure semantics."""

    code: str
    message: str
    context: dict[str, object]


def _load_verification_config() -> dict[str, object]:
    """Read the verification section from config."""
    config = load_config()
    raw = config.get("verification", {})
    if isinstance(raw, dict):
        return raw
    return {}


def _freshness_for_time_sensitivity(time_sensitivity: str) -> str:
    """Map project time-sensitivity into Brave-style freshness windows."""
    return _FRESHNESS_MAP.get(time_sensitivity, "pm")


def _estimate_recency(age: str) -> float:
    """Estimate recency score from Brave age strings."""
    if not age:
        return 0.5

    age_lower = age.lower()
    if "hour" in age_lower or "minute" in age_lower:
        return 0.95
    if "day" in age_lower:
        return 0.90
    if "week" in age_lower:
        return 0.80
    if "month" in age_lower:
        parts = age_lower.split()
        try:
            months = int(parts[0])
            return max(0.4, 0.80 - months * 0.05)
        except (ValueError, IndexError):
            return 0.65
    if "year" in age_lower:
        parts = age_lower.split()
        try:
            years = int(parts[0])
            return max(0.2, 0.50 - years * 0.05)
        except (ValueError, IndexError):
            return 0.5
    return 0.5


def _build_inconclusive_result(dispute_id: str, reason: str) -> ArbitrationResult:
    """Create a typed inconclusive arbitration result for explicit warning cases."""
    return ArbitrationResult(
        dispute_id=dispute_id,
        verdict="inconclusive",
        new_evidence_ids=[],
        reasoning=reason,
        claim_updates={},
    )


async def generate_verification_queries(
    disputes: list[Dispute],
    claims: list[Claim],
    trace_id: str,
    question_text: str = "",
    max_budget: float = 1.0,
) -> list[VerificationQueryBatch]:
    """Generate search queries for decision-critical disputes (Phase 4a).

    Returns one VerificationQueryBatch per dispute.
    """
    from llm_client import acall_llm_structured, render_prompt
    from pydantic import BaseModel

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
        question=question_text,
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
    available_evidence: list[EvidenceItem],
    fresh_evidence: list[EvidenceItem],
    trace_id: str,
    max_budget: float = 1.0,
) -> ArbitrationResult:
    """Arbitrate a single dispute using evidence plus fresh evidence (Phase 4b).

    Returns a typed ArbitrationResult with fresh evidence IDs constrained to newly
    fetched evidence. Non-evidence-backed supportive verdicts are forced to
    inconclusive.
    """
    from llm_client import acall_llm_structured, render_prompt

    fresh_evidence_ids = {item.id for item in fresh_evidence}
    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "arbitration.yaml"),
        dispute=dispute.model_dump(),
        claims=[c.model_dump() for c in claims],
        evidence=[e.model_dump() for e in available_evidence],
        fresh_evidence=[e.model_dump() for e in fresh_evidence],
    )

    model = get_model("arbitration")
    try:
        result, _meta = await acall_llm_structured(
            model,
            messages,
            response_model=ArbitrationResult,
            task="dispute_arbitration",
            trace_id=f"{trace_id}/arb/{dispute.id}",
            max_budget=max_budget,
        )
    except Exception as exc:
        return _build_inconclusive_result(
            dispute.id,
            f"Arbitration call failed before a decision: {exc}",
        )

    result.dispute_id = dispute.id
    result.new_evidence_ids = [eid for eid in result.new_evidence_ids if eid in fresh_evidence_ids]

    if result.verdict in {"supported", "revised", "refuted"} and not result.new_evidence_ids:
        result.verdict = "inconclusive"
        result.claim_updates = {}
        result.reasoning = (
            "The verdict was not supported by retrievable `new_evidence_ids`. "
            "Promoted to inconclusive under fail-loud rules."
        )

    return result


async def _collect_fresh_evidence_for_dispute(
    dispute: Dispute,
    queries: list[str],
    bundle: EvidenceBundle,
    trace_id: str,
 ) -> tuple[list[SourceRecord], list[EvidenceItem], list[VerificationWarning]]:
    """Run query search, read results, and convert to SourceRecord/EvidenceItems."""
    from grounded_research.tools.brave_search import search_web
    from grounded_research.tools.fetch_page import fetch_page
    from grounded_research.tools.jina_reader import fetch_page_jina

    cfg = _load_verification_config()
    max_results_per_query = int(cfg.get("results_per_query", 3))
    max_sources_per_dispute = int(cfg.get("max_new_sources_per_dispute", 3))
    freshness = _freshness_for_time_sensitivity(
        getattr(bundle.question, "time_sensitivity", "mixed")
    )

    seen_urls = {s.url for s in bundle.sources}
    seen_evidence_signatures: set[tuple[str, str]] = set()
    disputes_new_sources: list[SourceRecord] = []
    disputes_new_evidence: list[EvidenceItem] = []
    warnings: list[VerificationWarning] = []

    if not queries:
        warnings.append(VerificationWarning(
            code="verification_no_queries",
            message=f"No verification queries available for dispute {dispute.id}.",
            context={"dispute_id": dispute.id},
        ))
        return disputes_new_sources, disputes_new_evidence, warnings

    for query in queries:
        if len(disputes_new_sources) >= max_sources_per_dispute:
            break

        try:
            raw_results = await search_web(query, count=max_results_per_query, freshness=freshness)
            payload = json.loads(raw_results)
            search_results = payload.get("results", [])
        except Exception as exc:
            warnings.append(VerificationWarning(
                code="verification_search_failed",
                message=f"Search failed for dispute {dispute.id}: {exc}",
                context={"dispute_id": dispute.id, "query": query},
            ))
            continue

        if not search_results:
            warnings.append(VerificationWarning(
                code="verification_no_results",
                message=f"No search results for dispute {dispute.id}.",
                context={"dispute_id": dispute.id, "query": query},
            ))
            continue

        for result in search_results:
            if len(disputes_new_sources) >= max_sources_per_dispute:
                break

            url = (result.get("url") or "").strip()
            if not url or url in seen_urls:
                continue

            seen_urls.add(url)
            source = SourceRecord(
                url=url,
                title=(result.get("title") or url).strip(),
                source_type="web_search",
                quality_tier="reliable",
                recency_score=_estimate_recency(result.get("age", "")),
            )

            source_note = (result.get("description") or "").strip()
            if source_note:
                sig = (source.url, source_note[:80])
                if sig not in seen_evidence_signatures:
                    seen_evidence_signatures.add(sig)
                    disputes_new_evidence.append(EvidenceItem(
                        source_id=source.id,
                        content=source_note,
                        content_type="summary",
                        relevance_note=f"Search snippet for query: {query}",
                        extraction_method="upstream",
                    ))

            try:
                raw_page = await fetch_page(url, question=bundle.question.text if bundle.question else "")
                page = json.loads(raw_page)
            except Exception as exc:
                warnings.append(VerificationWarning(
                    code="verification_fetch_failed",
                    message=f"Direct fetch failed for dispute {dispute.id}: {exc}",
                    context={"dispute_id": dispute.id, "url": url},
                ))
                continue

            if page.get("error") and "403" in str(page.get("error")):
                try:
                    raw_page = await fetch_page_jina(url, question=bundle.question.text if bundle.question else "")
                    page = json.loads(raw_page)
                except Exception as exc:
                    warnings.append(VerificationWarning(
                        code="verification_fetch_failed",
                        message=f"Jina fallback failed for dispute {dispute.id}: {exc}",
                        context={"dispute_id": dispute.id, "url": url},
                    ))
                    continue

            if page.get("error"):
                warnings.append(VerificationWarning(
                    code="verification_fetch_failed",
                    message=f"Fetch returned error for dispute {dispute.id}: {page.get('error')}",
                    context={"dispute_id": dispute.id, "url": url},
                ))
                continue

            for text_field in ("key_section", "notes"):
                page_text = (page.get(text_field) or "").strip()
                if not page_text:
                    continue
                sig = (source.id, page_text[:100])
                if sig in seen_evidence_signatures:
                    continue
                seen_evidence_signatures.add(sig)
                disputes_new_evidence.append(EvidenceItem(
                    source_id=source.id,
                    content=page_text,
                    content_type="text",
                    relevance_note=f"{text_field} from {url} for dispute {dispute.id}",
                    extraction_method="llm",
                ))

            if source not in disputes_new_sources:
                disputes_new_sources.append(source)

    if not disputes_new_evidence:
        warnings.append(VerificationWarning(
            code="verification_no_fresh_evidence",
            message=f"No usable fresh evidence for dispute {dispute.id}.",
            context={"dispute_id": dispute.id},
        ))

    return disputes_new_sources, disputes_new_evidence, warnings


async def verify_disputes(
    ledger: ClaimLedger,
    bundle: EvidenceBundle,
    trace_id: str,
    max_disputes: int = 5,
    max_budget: float = 2.0,
) -> tuple[ClaimLedger, list[ArbitrationResult], list[VerificationWarning], int]:
    """Verify decision-critical disputes and update ledger state.

    Returns:
    - updated ClaimLedger
    - list of arbitration outcomes
    - explicit warnings describing partial failures
    - approximate llm call count incurred during verification
    """
    llm_calls = 0
    dispute_updates: list[VerificationWarning] = []

    actionable = [
        dispute
        for dispute in ledger.disputes
        if dispute.severity == "decision_critical"
        and dispute.route in {"verify", "arbitrate"}
        and not dispute.resolved
    ][:max_disputes]

    if not actionable:
        return ledger, [], [], llm_calls

    budget_per_dispute = max_budget / len(actionable)
    claim_map = {claim.id: claim for claim in ledger.claims}

    try:
        query_batches = await generate_verification_queries(
            actionable,
            list(ledger.claims),
            trace_id=trace_id,
            question_text=(bundle.question.text if bundle.question else ""),
            max_budget=min(budget_per_dispute, 0.5),
        )
        llm_calls += 1
        query_lookup = {batch.dispute_id: batch.queries for batch in query_batches}
    except Exception as exc:
        err = f"Verification query generation failed: {exc}"
        for d in actionable:
            dispute_updates.append(VerificationWarning(
                code="verification_query_generation_failed",
                message=err,
                context={"dispute_id": d.id},
            ))
        arbitration_results = [_build_inconclusive_result(d.id, err) for d in actionable]
        ledger.arbitration_results = arbitration_results
        return ledger, arbitration_results, dispute_updates, llm_calls + 1

    arbitration_results: list[ArbitrationResult] = []
    for dispute in actionable:
        queries = query_lookup.get(dispute.id) or []
        new_sources, new_evidence, warnings = await _collect_fresh_evidence_for_dispute(
            dispute=dispute,
            queries=queries,
            bundle=bundle,
            trace_id=f"{trace_id}/verify/{dispute.id}",
        )
        dispute_updates.extend(warnings)

        if not new_evidence:
            arbitration_results.append(
                _build_inconclusive_result(dispute.id, "No fresh evidence discovered.")
            )
            continue

        bundle.sources.extend(new_sources)
        bundle.evidence.extend(new_evidence)

        relevant_claims = [claim_map[cid] for cid in dispute.claim_ids if cid in claim_map]
        relevant_evidence_ids: set[str] = set()
        for c in relevant_claims:
            relevant_evidence_ids.update(c.evidence_ids)
        evidence = [e for e in bundle.evidence if e.id in relevant_evidence_ids]
        evidence.extend(new_evidence)

        result = await arbitrate_dispute(
            dispute=dispute,
            claims=relevant_claims,
            available_evidence=evidence,
            fresh_evidence=new_evidence,
            trace_id=trace_id,
            max_budget=budget_per_dispute,
        )
        llm_calls += 1

        if result.verdict != "inconclusive" and not result.new_evidence_ids:
            dispute_updates.append(VerificationWarning(
                code="verification_no_fresh_ids",
                message=f"Dispute {dispute.id} verdict had no fresh evidence IDs.",
                context={"dispute_id": dispute.id, "verdict": result.verdict},
            ))
            result = _build_inconclusive_result(
                dispute.id,
                "Arbitration did not return valid fresh-evidence IDs.",
            )

        if result.verdict != "inconclusive":
            dispute.resolved = True
            dispute.resolution_summary = result.reasoning[:200]
            for claim_id, new_status in result.claim_updates.items():
                claim = ledger.claim_by_id(claim_id)
                if claim is None:
                    dispute_updates.append(VerificationWarning(
                        code="verification_missing_claim",
                        message=f"Arbitration references unknown claim {claim_id}.",
                        context={"dispute_id": dispute.id, "claim_id": claim_id},
                    ))
                    continue
                claim.status = new_status
                claim.status_reason = f"Arbitration {result.id}: {result.verdict}"
        else:
            dispute.resolved = False
            dispute.resolution_summary = result.reasoning[:200]

        arbitration_results.append(result)

    resolved_count = sum(1 for d in actionable if d.resolved)
    if resolved_count == 0 and actionable:
        dispute_updates.append(VerificationWarning(
            code="verification_no_resolutions",
            message="No dispute produced a concrete resolution in this run.",
            context={"dispute_ids": [d.id for d in actionable]},
        ))

    max_turns = int(get_budget("verification_max_turns"))
    if max_turns < 1:
        dispute_updates.append(VerificationWarning(
            code="verification_bad_budget",
            message="verification_max_turns is < 1 in config.",
            context={"dispute_count": len(actionable), "max_turns": max_turns},
        ))

    ledger.arbitration_results = arbitration_results
    return ledger, arbitration_results, dispute_updates, llm_calls
