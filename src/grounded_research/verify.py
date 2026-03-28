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

from grounded_research.config import get_budget, get_depth_config, get_fallback_models, get_model, load_config
from grounded_research.models import (
    ArbitrationResult,
    Claim,
    ClaimUpdate,
    ClaimLedger,
    Dispute,
    EvidenceBundle,
    EvidenceItem,
    QuestionDecomposition,
    SourceRecord,
    VerificationQueryBatch,
)
from grounded_research.tyler_v1_adapters import (
    current_bundle_to_tyler_evidence_package,
    normalize_tyler_claim_extraction_result,
    tyler_stage5_to_current_ledger,
)
from grounded_research.tyler_v1_models import (
    AdditionalSource,
    ArbitrationAssessment,
    ClaimExtractionResult as TylerClaimExtractionResult,
    ClaimStatus as TylerClaimStatus,
    ClaimStatusUpdate,
    DisputeQueueEntry,
    DisputeStatus,
    ResolutionOutcome,
    VerificationResult,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

from grounded_research.evidence_utils import FRESHNESS_MAP as _FRESHNESS_MAP
from grounded_research.runtime_policy import get_request_timeout


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


from grounded_research.evidence_utils import estimate_recency as _estimate_recency


def _build_inconclusive_result(dispute_id: str, reason: str) -> ArbitrationResult:
    """Create a typed inconclusive arbitration result for explicit warning cases."""
    return ArbitrationResult(
        dispute_id=dispute_id,
        verdict="inconclusive",
        new_evidence_ids=[],
        reasoning=reason,
        claim_updates=[],
    )


def _validate_claim_updates(
    dispute: Dispute,
    updates: list[ClaimUpdate],
    claim_map: dict[str, Claim],
    fresh_evidence_ids: set[str],
) -> tuple[list[ClaimUpdate], list[VerificationWarning]]:
    """Filter arbitration claim updates to the protocol-valid subset.

    The anti-conformity contract is enforced here, not left to prompt wording:
    every live claim change must target a disputed claim, cite retrieved fresh
    evidence, and provide a non-empty justification.
    """
    warnings: list[VerificationWarning] = []
    valid_updates: list[ClaimUpdate] = []
    seen_claim_ids: set[str] = set()
    dispute_claim_ids = set(dispute.claim_ids)

    for update in updates:
        if update.claim_id in seen_claim_ids:
            warnings.append(VerificationWarning(
                code="verification_duplicate_claim_update",
                message=f"Duplicate claim update for {update.claim_id} in dispute {dispute.id}.",
                context={"dispute_id": dispute.id, "claim_id": update.claim_id},
            ))
            continue

        if update.claim_id not in claim_map:
            warnings.append(VerificationWarning(
                code="verification_missing_claim",
                message=f"Arbitration references unknown claim {update.claim_id}.",
                context={"dispute_id": dispute.id, "claim_id": update.claim_id},
            ))
            continue

        if update.claim_id not in dispute_claim_ids:
            warnings.append(VerificationWarning(
                code="verification_claim_outside_dispute",
                message=f"Arbitration tried to update claim {update.claim_id} outside dispute {dispute.id}.",
                context={"dispute_id": dispute.id, "claim_id": update.claim_id},
            ))
            continue

        if update.new_status == "initial":
            warnings.append(VerificationWarning(
                code="verification_invalid_claim_status",
                message=f"Arbitration returned non-terminal status 'initial' for claim {update.claim_id}.",
                context={"dispute_id": dispute.id, "claim_id": update.claim_id, "new_status": update.new_status},
            ))
            continue

        cited_fresh_ids = [eid for eid in update.cited_evidence_ids if eid in fresh_evidence_ids]
        if not cited_fresh_ids:
            warnings.append(VerificationWarning(
                code="verification_claim_update_missing_fresh_evidence",
                message=f"Claim update for {update.claim_id} lacks valid fresh evidence IDs.",
                context={
                    "dispute_id": dispute.id,
                    "claim_id": update.claim_id,
                    "cited_evidence_ids": update.cited_evidence_ids,
                },
            ))
            continue

        if not update.justification.strip():
            warnings.append(VerificationWarning(
                code="verification_claim_update_missing_justification",
                message=f"Claim update for {update.claim_id} has empty justification.",
                context={"dispute_id": dispute.id, "claim_id": update.claim_id},
            ))
            continue

        valid_updates.append(
            update.model_copy(update={"cited_evidence_ids": cited_fresh_ids})
        )
        seen_claim_ids.add(update.claim_id)

    return valid_updates, warnings


def _enforce_arbitration_protocol(
    dispute: Dispute,
    result: ArbitrationResult,
    claim_map: dict[str, Claim],
    fresh_evidence_ids: set[str],
) -> tuple[ArbitrationResult, list[VerificationWarning]]:
    """Apply protocol-level validation to arbitration output.

    A non-inconclusive verdict survives only if it cites fresh evidence and
    carries at least one valid structured claim update.
    """
    warnings: list[VerificationWarning] = []
    valid_new_evidence_ids = [eid for eid in result.new_evidence_ids if eid in fresh_evidence_ids]

    if result.verdict == "inconclusive":
        if result.claim_updates:
            warnings.append(VerificationWarning(
                code="verification_inconclusive_with_updates",
                message=f"Inconclusive arbitration for {dispute.id} returned claim updates; dropping them.",
                context={"dispute_id": dispute.id, "claim_update_count": len(result.claim_updates)},
            ))
        return result.model_copy(
            update={
                "new_evidence_ids": valid_new_evidence_ids,
                "claim_updates": [],
            }
        ), warnings

    if not valid_new_evidence_ids:
        warnings.append(VerificationWarning(
            code="verification_no_fresh_ids",
            message=f"Dispute {dispute.id} verdict had no valid fresh evidence IDs.",
            context={"dispute_id": dispute.id, "verdict": result.verdict},
        ))
        return _build_inconclusive_result(
            dispute.id,
            "Arbitration did not return valid fresh-evidence IDs.",
        ), warnings

    valid_updates, update_warnings = _validate_claim_updates(
        dispute=dispute,
        updates=result.claim_updates,
        claim_map=claim_map,
        fresh_evidence_ids=set(valid_new_evidence_ids),
    )
    warnings.extend(update_warnings)

    if not valid_updates:
        warnings.append(VerificationWarning(
            code="verification_no_valid_claim_updates",
            message=f"Dispute {dispute.id} produced no protocol-valid claim updates.",
            context={"dispute_id": dispute.id, "verdict": result.verdict},
        ))
        return _build_inconclusive_result(
            dispute.id,
            "Arbitration did not produce any protocol-valid claim updates tied to fresh evidence.",
        ), warnings

    return result.model_copy(
        update={
            "new_evidence_ids": valid_new_evidence_ids,
            "claim_updates": valid_updates,
        }
    ), warnings


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
        timeout=get_request_timeout("verification_query_generation"),
        max_budget=max_budget,
        fallback_models=get_fallback_models("arbitration"),
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

    Returns a typed ArbitrationResult using an LLM-facing response schema that
    excludes system-assigned fields. Protocol validation happens after the call.
    """
    import random as _random
    from llm_client import acall_llm_structured, render_prompt
    from pydantic import BaseModel, Field

    # Shuffle claim order to prevent primacy bias (#38)
    shuffled_claims = list(claims)
    _random.Random(dispute.id).shuffle(shuffled_claims)

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "arbitration.yaml"),
        dispute=dispute.model_dump(),
        claims=[c.model_dump() for c in shuffled_claims],
        evidence=[e.model_dump() for e in available_evidence],
        fresh_evidence=[e.model_dump() for e in fresh_evidence],
    )

    class ArbitrationDecision(BaseModel):
        """LLM-facing arbitration payload without system-assigned fields."""

        verdict: str = Field(description="supported, revised, refuted, or inconclusive")
        new_evidence_ids: list[str] = Field(
            default_factory=list,
            description="Fresh evidence IDs that materially support the verdict.",
        )
        reasoning: str = Field(description="Reasoning chain for the verdict.")
        claim_updates: list[ClaimUpdate] = Field(
            default_factory=list,
            description="Structured claim-level updates justified by the fresh evidence.",
        )

    model = get_model("arbitration")
    try:
        result, _meta = await acall_llm_structured(
            model,
            messages,
            response_model=ArbitrationDecision,
            task="dispute_arbitration",
            trace_id=f"{trace_id}/arb/{dispute.id}",
            timeout=get_request_timeout("arbitration"),
            max_budget=max_budget,
            fallback_models=get_fallback_models("arbitration"),
        )
    except Exception as exc:
        return _build_inconclusive_result(
            dispute.id,
            f"Arbitration call failed before a decision: {exc}",
        )

    verdict = result.verdict if result.verdict in {"supported", "revised", "refuted", "inconclusive"} else "inconclusive"
    return ArbitrationResult(
        dispute_id=dispute.id,
        verdict=verdict,
        new_evidence_ids=result.new_evidence_ids,
        reasoning=result.reasoning,
        claim_updates=result.claim_updates,
    )


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
            raw_results = await search_web(
                query,
                count=max_results_per_query,
                freshness=freshness,
                trace_id=f"{trace_id}/search/{dispute.id}",
                task="verification.search",
            )
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


def _build_tyler_verification_queries(
    dispute: DisputeQueueEntry,
    claim_statements: list[str],
    original_query: str,
) -> list[str]:
    """Deterministically construct Tyler-style neutral verification queries."""
    base = dispute.description or original_query
    first_claim = claim_statements[0] if claim_statements else original_query
    second_claim = claim_statements[1] if len(claim_statements) > 1 else first_claim
    year = "2026"
    return [
        f"{base} evidence",
        f"{first_claim} versus {second_claim}",
        f"{base} official study {year}",
    ]


def _build_additional_sources(
    *,
    dispute_id: str,
    new_sources: list[SourceRecord],
    new_evidence: list[EvidenceItem],
) -> list[AdditionalSource]:
    """Convert freshly fetched evidence into Tyler's Stage 5 source shape."""
    evidence_by_source: dict[str, list[str]] = {}
    for item in new_evidence:
        evidence_by_source.setdefault(item.source_id, []).append(item.content)
    return [
        AdditionalSource(
            source_id=source.id,
            url=source.url,
            title=source.title,
            quality_score={
                "authoritative": 0.9,
                "reliable": 0.75,
                "unknown": 0.5,
                "unreliable": 0.2,
            }.get(source.quality_tier, 0.5),
            key_findings=evidence_by_source.get(source.id, []),
            retrieved_for_dispute=dispute_id,
        )
        for source in new_sources
    ]


async def arbitrate_dispute_tyler_v1(
    *,
    original_query: str,
    dispute: DisputeQueueEntry,
    claim_ledger_entries: list[object],
    relevant_original_sources: list[object],
    new_evidence: list[AdditionalSource],
    trace_id: str,
    max_budget: float,
) -> ArbitrationAssessment:
    """Run Tyler's literal Stage 5 arbitration prompt for one dispute."""
    from llm_client import acall_llm_structured, render_prompt

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "tyler_v1_arbitration.yaml"),
        original_query=original_query,
        dispute=dispute.model_dump(mode="json"),
        claim_ledger=[claim.model_dump(mode="json") for claim in claim_ledger_entries],
        relevant_original_sources=[source.model_dump(mode="json") for source in relevant_original_sources],
        new_evidence=[source.model_dump(mode="json") for source in new_evidence],
        response_schema_json=ArbitrationAssessment.model_json_schema(),
    )
    model = get_model("arbitration")
    result, _meta = await acall_llm_structured(
        model,
        messages,
        response_model=ArbitrationAssessment,
        task="dispute_arbitration_tyler_v1",
        trace_id=f"{trace_id}/arb/{dispute.id}",
        timeout=get_request_timeout("arbitration"),
        max_budget=max_budget,
        fallback_models=get_fallback_models("arbitration"),
    )
    return result


def _normalize_tyler_claim_status_updates(
    *,
    dispute: DisputeQueueEntry,
    claim_ids: list[str],
    assessment: ArbitrationAssessment,
) -> list[ClaimStatusUpdate]:
    """Repair arbitration claim-status updates into Tyler's strict post-Stage-5 set."""
    allowed = {
        TylerClaimStatus.VERIFIED,
        TylerClaimStatus.REFUTED,
        TylerClaimStatus.UNRESOLVED,
    }
    normalized: list[ClaimStatusUpdate] = []
    seen: set[str] = set()
    default_status = {
        ResolutionOutcome.CLAIM_SUPPORTED: TylerClaimStatus.VERIFIED,
        ResolutionOutcome.CLAIM_REFUTED: TylerClaimStatus.REFUTED,
        ResolutionOutcome.INTERPRETATION_REVISED: TylerClaimStatus.VERIFIED,
        ResolutionOutcome.EVIDENCE_INSUFFICIENT: TylerClaimStatus.UNRESOLVED,
    }[assessment.resolution]
    for update in assessment.updated_claim_statuses:
        if update.claim_id not in claim_ids or update.claim_id in seen:
            continue
        status = update.new_status if update.new_status in allowed else default_status
        normalized.append(
            update.model_copy(
                update={
                    "new_status": status,
                    "remaining_uncertainty": update.remaining_uncertainty
                    or (
                        assessment.new_evidence_summary
                        if assessment.resolution is ResolutionOutcome.EVIDENCE_INSUFFICIENT
                        else None
                    ),
                }
            )
        )
        seen.add(update.claim_id)

    if normalized:
        return normalized

    return [
        ClaimStatusUpdate(
            claim_id=claim_id,
            new_status=default_status,
            confidence_in_resolution=assessment.updated_claim_statuses[0].confidence_in_resolution
            if assessment.updated_claim_statuses
            else "medium",
            remaining_uncertainty=assessment.new_evidence_summary
            if default_status is TylerClaimStatus.UNRESOLVED
            else None,
        )
        for claim_id in claim_ids
    ]


async def verify_disputes_tyler_v1(
    *,
    stage_4_result: TylerClaimExtractionResult,
    prior_ledger: ClaimLedger,
    bundle: EvidenceBundle,
    decomposition: QuestionDecomposition | None,
    stage_1_result: DecompositionResult | None = None,
    stage_2_result: EvidencePackage | None = None,
    trace_id: str,
    max_disputes: int = 5,
    max_budget: float = 2.0,
) -> tuple[VerificationResult, ClaimLedger, list[VerificationWarning], int]:
    """Run Tyler's Stage 5 artifact and project it into the shipped ledger."""
    original_query = bundle.question.text if bundle.question else ""
    if stage_1_result is not None:
        tyler_stage1 = stage_1_result
    else:
        from grounded_research.decompose import decompose_question_tyler_v1

        tyler_stage1 = await decompose_question_tyler_v1(
            question=original_query,
            trace_id=f"{trace_id}/stage1_for_verify",
            max_budget=max_budget * 0.1,
        )
    if stage_2_result is None:
        stage_2_result = current_bundle_to_tyler_evidence_package(
            bundle,
            tyler_stage1,
            current_decomposition=decomposition,
        )
    claim_lookup = {claim.id: claim.model_copy(deep=True) for claim in stage_4_result.claim_ledger}
    dispute_lookup = {dispute.id: dispute.model_copy(deep=True) for dispute in stage_4_result.dispute_queue}
    actionable = [
        dispute
        for dispute in stage_4_result.dispute_queue
        if dispute.decision_critical
        and dispute.resolution_routing in {"stage_5_evidence", "stage_5_arbitration"}
        and dispute.status is DisputeStatus.UNRESOLVED
    ][:max_disputes]

    if not actionable:
        empty = VerificationResult(
            disputes_investigated=[],
            additional_sources=[],
            updated_claim_ledger=stage_4_result.claim_ledger,
            updated_dispute_queue=stage_4_result.dispute_queue,
            search_budget={},
            rounds_used=0,
            stage_summary={
                "stage_name": "Stage 5: Targeted Verification & Arbitration",
                "goal": "Resolve decision-critical empirical and interpretive disputes.",
                "key_findings": ["No decision-critical Stage 5 disputes required investigation."],
                "decisions_made": ["Skipped Stage 5 because no actionable disputes remained."],
                "outcome": "No verification work performed.",
                "reasoning": "The Stage 4 dispute queue had no unresolved empirical or interpretive decision-critical disputes.",
            },
        )
        return empty, prior_ledger, [], 0

    depth_cfg = get_depth_config()
    max_rounds = max(1, int(depth_cfg.get("arbitration_max_rounds", 1)))
    budget_per_dispute = max_budget / len(actionable)
    llm_calls = 0
    warnings: list[VerificationWarning] = []
    all_additional_sources: list[AdditionalSource] = []
    investigated: list[ArbitrationAssessment] = []
    search_budget: dict[str, int] = {}
    rounds_used = 0

    for dispute in actionable:
        current_dispute = next((item for item in prior_ledger.disputes if item.id == dispute.id), None)
        if current_dispute is None:
            continue
        claim_entries = [claim_lookup[claim_id] for claim_id in dispute.claims_involved if claim_id in claim_lookup]
        relevant_original_sources = [
            source
            for subq in stage_2_result.sub_question_evidence
            for source in subq.sources
            if any(source.id in claim.source_references for claim in claim_entries)
        ]
        latest_assessment = ArbitrationAssessment(
            dispute_id=dispute.id,
            new_evidence_summary="Verification did not run.",
            reasoning="Verification did not run.",
            resolution=ResolutionOutcome.EVIDENCE_INSUFFICIENT,
            updated_claim_statuses=[
                ClaimStatusUpdate(
                    claim_id=claim.id,
                    new_status=TylerClaimStatus.UNRESOLVED,
                    confidence_in_resolution="medium",
                    remaining_uncertainty="Verification did not run.",
                )
                for claim in claim_entries
            ],
        )

        for round_idx in range(1, max_rounds + 1):
            rounds_used = max(rounds_used, round_idx)
            round_trace_id = f"{trace_id}/verify_tyler/{dispute.id}/round_{round_idx}"
            round_budget = budget_per_dispute / max_rounds
            queries = _build_tyler_verification_queries(
                dispute,
                [claim.statement for claim in claim_entries],
                original_query,
            )
            search_budget[dispute.id] = search_budget.get(dispute.id, 0) + len(queries)

            new_sources, new_evidence, new_warnings = await _collect_fresh_evidence_for_dispute(
                dispute=current_dispute,
                queries=queries,
                bundle=bundle,
                trace_id=round_trace_id,
            )
            warnings.extend(new_warnings)
            additional_sources = _build_additional_sources(
                dispute_id=dispute.id,
                new_sources=new_sources,
                new_evidence=new_evidence,
            )
            all_additional_sources.extend(additional_sources)

            if not additional_sources:
                latest_assessment = latest_assessment.model_copy(
                    update={
                        "new_evidence_summary": f"No fresh evidence discovered in round {round_idx}.",
                        "reasoning": f"No fresh evidence discovered in round {round_idx}.",
                        "resolution": ResolutionOutcome.EVIDENCE_INSUFFICIENT,
                        "updated_claim_statuses": [
                            ClaimStatusUpdate(
                                claim_id=claim.id,
                                new_status=TylerClaimStatus.UNRESOLVED,
                                confidence_in_resolution="medium",
                                remaining_uncertainty=f"No fresh evidence discovered in round {round_idx}.",
                            )
                            for claim in claim_entries
                        ],
                    }
                )
                break

            assessment = await arbitrate_dispute_tyler_v1(
                original_query=original_query,
                dispute=dispute,
                claim_ledger_entries=claim_entries,
                relevant_original_sources=relevant_original_sources,
                new_evidence=additional_sources,
                trace_id=round_trace_id,
                max_budget=round_budget,
            )
            llm_calls += 1
            normalized_updates = _normalize_tyler_claim_status_updates(
                dispute=dispute,
                claim_ids=[claim.id for claim in claim_entries],
                assessment=assessment,
            )
            latest_assessment = assessment.model_copy(update={"updated_claim_statuses": normalized_updates})
            if assessment.resolution is not ResolutionOutcome.EVIDENCE_INSUFFICIENT:
                break

        investigated.append(latest_assessment)
        if latest_assessment.resolution is ResolutionOutcome.EVIDENCE_INSUFFICIENT:
            dispute_lookup[dispute.id].status = DisputeStatus.UNRESOLVED
        else:
            dispute_lookup[dispute.id].status = DisputeStatus.RESOLVED
        for update in latest_assessment.updated_claim_statuses:
            if update.claim_id in claim_lookup:
                claim_lookup[update.claim_id].status = update.new_status

    verification_result = VerificationResult(
        disputes_investigated=investigated,
        additional_sources=all_additional_sources,
        updated_claim_ledger=list(claim_lookup.values()),
        updated_dispute_queue=list(dispute_lookup.values()),
        search_budget=search_budget,
        rounds_used=rounds_used,
        stage_summary={
            "stage_name": "Stage 5: Targeted Verification & Arbitration",
            "goal": "Resolve decision-critical empirical and interpretive disputes with targeted fresh evidence.",
            "key_findings": [
                f"{len(investigated)} disputes investigated",
                f"{len(all_additional_sources)} additional sources gathered",
                f"{sum(1 for item in investigated if item.resolution is not ResolutionOutcome.EVIDENCE_INSUFFICIENT)} disputes resolved",
            ],
            "decisions_made": [
                "Used deterministic neutral verification queries per dispute",
                "Updated only claims directly involved in investigated disputes",
            ],
            "outcome": f"Stage 5 completed with {rounds_used} round(s) used.",
            "reasoning": "Literal Tyler Stage 5 arbitration ran against targeted fresh evidence, then the result was normalized into strict post-verification claim statuses.",
        },
    )
    current_ledger = tyler_stage5_to_current_ledger(verification_result, prior_ledger)
    return verification_result, current_ledger, warnings, llm_calls


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

    depth_cfg = get_depth_config()
    max_rounds = max(1, int(depth_cfg.get("arbitration_max_rounds", 1)))
    budget_per_dispute = max_budget / len(actionable)
    claim_map = {claim.id: claim for claim in ledger.claims}

    arbitration_results: list[ArbitrationResult] = []
    for dispute in actionable:
        relevant_claims = [claim_map[cid] for cid in dispute.claim_ids if cid in claim_map]
        cumulative_fresh_evidence: list[EvidenceItem] = []
        latest_result = _build_inconclusive_result(
            dispute.id,
            "Verification did not run.",
        )

        for round_idx in range(1, max_rounds + 1):
            round_trace_id = f"{trace_id}/verify/{dispute.id}/round_{round_idx}"
            round_budget = budget_per_dispute / max_rounds
            try:
                query_batches = await generate_verification_queries(
                    [dispute],
                    relevant_claims,
                    trace_id=round_trace_id,
                    question_text=(bundle.question.text if bundle.question else ""),
                    max_budget=min(round_budget, 0.5),
                )
                llm_calls += 1
                queries = query_batches[0].queries if query_batches else []
            except Exception as exc:
                err = f"Verification query generation failed: {exc}"
                dispute_updates.append(VerificationWarning(
                    code="verification_query_generation_failed",
                    message=err,
                    context={"dispute_id": dispute.id, "round": round_idx},
                ))
                latest_result = _build_inconclusive_result(dispute.id, err)
                break

            new_sources, new_evidence, warnings = await _collect_fresh_evidence_for_dispute(
                dispute=dispute,
                queries=queries,
                bundle=bundle,
                trace_id=round_trace_id,
            )
            dispute_updates.extend(warnings)

            if not new_evidence:
                latest_result = _build_inconclusive_result(
                    dispute.id,
                    f"No fresh evidence discovered in round {round_idx}.",
                )
                dispute_updates.append(VerificationWarning(
                    code="verification_round_stopped_no_fresh_evidence",
                    message=(
                        f"Verification stopped after round {round_idx} for dispute "
                        f"{dispute.id} because no new evidence was discovered."
                    ),
                    context={"dispute_id": dispute.id, "round": round_idx},
                ))
                break

            bundle.sources.extend(new_sources)
            bundle.evidence.extend(new_evidence)
            cumulative_fresh_evidence.extend(new_evidence)

            relevant_evidence_ids: set[str] = set()
            for c in relevant_claims:
                relevant_evidence_ids.update(c.evidence_ids)
            evidence = [e for e in bundle.evidence if e.id in relevant_evidence_ids]
            evidence.extend(cumulative_fresh_evidence)

            result = await arbitrate_dispute(
                dispute=dispute,
                claims=relevant_claims,
                available_evidence=evidence,
                fresh_evidence=cumulative_fresh_evidence,
                trace_id=round_trace_id,
                max_budget=round_budget,
            )
            llm_calls += 1

            result, protocol_warnings = _enforce_arbitration_protocol(
                dispute=dispute,
                result=result,
                claim_map=claim_map,
                fresh_evidence_ids={item.id for item in cumulative_fresh_evidence},
            )
            dispute_updates.extend(protocol_warnings)
            latest_result = result

            if result.verdict != "inconclusive":
                break

        if latest_result.verdict != "inconclusive":
            dispute.resolved = True
            dispute.resolution_summary = latest_result.reasoning[:200]
            for update in latest_result.claim_updates:
                claim = ledger.claim_by_id(update.claim_id)
                if claim is None:
                    dispute_updates.append(VerificationWarning(
                        code="verification_missing_claim",
                        message=f"Arbitration references unknown claim {update.claim_id}.",
                        context={"dispute_id": dispute.id, "claim_id": update.claim_id},
                    ))
                    continue
                claim.status = update.new_status
                claim_map[claim.id] = claim
                cited = ", ".join(update.cited_evidence_ids[:3])
                claim.status_reason = (
                    f"Arbitration {latest_result.id} ({update.basis_type}; evidence {cited}): "
                    f"{update.justification}"
                )
        else:
            dispute.resolved = False
            dispute.resolution_summary = latest_result.reasoning[:200]
            if max_rounds > 1:
                dispute_updates.append(VerificationWarning(
                    code="verification_round_cap_hit",
                    message=(
                        f"Dispute {dispute.id} remained inconclusive after {max_rounds} "
                        "verification rounds."
                    ),
                    context={"dispute_id": dispute.id, "rounds": max_rounds},
                ))

        arbitration_results.append(latest_result)

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
