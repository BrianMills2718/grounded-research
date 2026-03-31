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
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from grounded_research.config import get_budget, get_depth_config, get_fallback_models, get_model, load_config
from grounded_research.models import (
    EvidenceBundle,
    EvidenceItem,
    SourceRecord,
)
from grounded_research.tyler_v1_models import (
    AdditionalSource,
    ArbitrationAssessment,
    ClaimExtractionResult as TylerClaimExtractionResult,
    ClaimLedgerEntry,
    ClaimStatus as TylerClaimStatus,
    ClaimStatusUpdate,
    DisputeQueueEntry,
    DisputeStatus,
    ResolutionOutcome,
    Source as TylerSource,
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
    """Map project time-sensitivity into shared-provider freshness windows."""
    return _FRESHNESS_MAP.get(time_sensitivity, "pm")

async def _collect_fresh_evidence_for_dispute(
    dispute_id: str,
    queries: list[str],
    bundle: EvidenceBundle,
    trace_id: str,
 ) -> tuple[list[SourceRecord], list[EvidenceItem], list[VerificationWarning]]:
    """Run query search, read results, and convert to SourceRecord/EvidenceItems."""
    from grounded_research.tools.web_search import search_web
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
            message=f"No verification queries available for dispute {dispute_id}.",
            context={"dispute_id": dispute_id},
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
                trace_id=f"{trace_id}/search/{dispute_id}",
                task="verification.search",
            )
            payload = json.loads(raw_results)
            search_results = payload.get("results", [])
        except Exception as exc:
            warnings.append(VerificationWarning(
                code="verification_search_failed",
                message=f"Search failed for dispute {dispute_id}: {exc}",
                context={"dispute_id": dispute_id, "query": query},
            ))
            continue

        if not search_results:
            warnings.append(VerificationWarning(
                code="verification_no_results",
                message=f"No search results for dispute {dispute_id}.",
                context={"dispute_id": dispute_id, "query": query},
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
                    message=f"Direct fetch failed for dispute {dispute_id}: {exc}",
                    context={"dispute_id": dispute_id, "url": url},
                ))
                continue

            if page.get("error") and "403" in str(page.get("error")):
                try:
                    raw_page = await fetch_page_jina(url, question=bundle.question.text if bundle.question else "")
                    page = json.loads(raw_page)
                except Exception as exc:
                    warnings.append(VerificationWarning(
                        code="verification_fetch_failed",
                        message=f"Jina fallback failed for dispute {dispute_id}: {exc}",
                        context={"dispute_id": dispute_id, "url": url},
                    ))
                    continue

            if page.get("error"):
                warnings.append(VerificationWarning(
                    code="verification_fetch_failed",
                    message=f"Fetch returned error for dispute {dispute_id}: {page.get('error')}",
                    context={"dispute_id": dispute_id, "url": url},
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
                    relevance_note=f"{text_field} from {url} for dispute {dispute_id}",
                    extraction_method="llm",
                ))

            if source not in disputes_new_sources:
                disputes_new_sources.append(source)

    if not disputes_new_evidence:
        warnings.append(VerificationWarning(
            code="verification_no_fresh_evidence",
            message=f"No usable fresh evidence for dispute {dispute_id}.",
            context={"dispute_id": dispute_id},
        ))

    return disputes_new_sources, disputes_new_evidence, warnings


def _build_tyler_verification_queries(
    *,
    dispute: DisputeQueueEntry,
    claim_entries: list[ClaimLedgerEntry],
    relevant_original_sources: list[TylerSource],
    original_query: str,
    time_sensitivity: str,
) -> list[str]:
    """Construct Tyler-literal verification queries.

    Tyler V1 spec §Stage 5: "generate counterfactual queries aimed at
    refuting the leading claim" with patterns: "[topic] limitations",
    "[claim] contradicted by".
    """
    neutral_query = _build_neutral_verification_question(
        dispute=dispute,
        claim_entries=claim_entries,
        original_query=original_query,
    )
    weaker_claim = _select_weaker_claim_for_verification(claim_entries)
    leading_claim = _select_leading_claim_for_refutation(claim_entries)

    # Tyler spec: counterfactual queries include limitations + contradicted-by
    queries = [
        neutral_query,
        _build_limitations_query(dispute, claim_entries, original_query),
        _build_refutation_query(leading_claim, neutral_query),
    ]
    if time_sensitivity == "time_sensitive":
        authoritative_query = _build_authoritative_verification_query(
            dispute=dispute,
            claim_entries=claim_entries,
            relevant_original_sources=relevant_original_sources,
            original_query=original_query,
        )
        queries.append(_build_dated_verification_query(authoritative_query))
    return queries


def _strip_terminal_punctuation(text: str) -> str:
    """Normalize terminal punctuation so query builders stay deterministic."""
    return text.strip().rstrip(".!?")


def _build_neutral_verification_question(
    *,
    dispute: DisputeQueueEntry,
    claim_entries: list[ClaimLedgerEntry],
    original_query: str,
) -> str:
    """Convert a dispute into a neutral question without presupposing either side."""
    description = _strip_terminal_punctuation(dispute.description or "")
    if description.lower().startswith("whether "):
        predicate = _normalize_whether_predicate(description[8:])
        if predicate.lower().startswith("there "):
            return f"Was {predicate}?"
        return f"Did {predicate}?"
    if description.endswith("?"):
        return description
    if description:
        return f"What does the evidence show about {description.lower()}?"
    if claim_entries:
        return f"What does the evidence show about {_strip_terminal_punctuation(claim_entries[0].statement).lower()}?"
    return f"What does the evidence show about {_strip_terminal_punctuation(original_query)}?"


def _normalize_whether_predicate(predicate: str) -> str:
    """Turn a 'whether X happened' predicate into a natural neutral-question predicate."""
    words = predicate.split()
    if not words:
        return predicate
    last_word = words[-1]
    if re.fullmatch(r"[A-Za-z]+ed", last_word):
        words[-1] = f"{last_word[:-1]}"
    return " ".join(words)


def _claim_support_score(claim: ClaimLedgerEntry) -> tuple[int, int, str]:
    """Rank claims by support so Stage 5 can target the weaker position deterministically."""
    return (
        len(claim.supporting_models) - len(claim.contesting_models),
        len(claim.supporting_models),
        claim.id,
    )


def _select_weaker_claim_for_verification(
    claim_entries: list[ClaimLedgerEntry],
) -> ClaimLedgerEntry | None:
    """Choose the less-supported claim so verification counteracts confirmation bias."""
    if not claim_entries:
        return None
    return min(claim_entries, key=_claim_support_score)


def _build_weaker_position_support_query(statement: str) -> str:
    """Generate a query seeking evidence for the currently weaker position."""
    return f"{_strip_terminal_punctuation(statement)} evidence study report"


def _select_leading_claim_for_refutation(
    claim_entries: list[ClaimLedgerEntry],
) -> ClaimLedgerEntry | None:
    """Choose the best-supported claim so refutation queries can target it."""
    if not claim_entries:
        return None
    return max(claim_entries, key=_claim_support_score)


def _build_limitations_query(
    dispute: DisputeQueueEntry,
    claim_entries: list[ClaimLedgerEntry],
    original_query: str,
) -> str:
    """Tyler V1 spec counterfactual pattern: '[topic] limitations'."""
    topic = _strip_terminal_punctuation(dispute.description or "")
    if topic.lower().startswith("whether "):
        topic = _normalize_whether_predicate(topic[8:])
    if not topic and claim_entries:
        topic = _strip_terminal_punctuation(claim_entries[0].statement)
    if not topic:
        topic = _strip_terminal_punctuation(original_query)
    return f"{topic} limitations"


def _build_refutation_query(
    leading_claim: ClaimLedgerEntry | None,
    fallback_query: str,
) -> str:
    """Tyler V1 spec counterfactual pattern: '[claim] contradicted by'."""
    if leading_claim:
        statement = _strip_terminal_punctuation(leading_claim.statement)
        return f"{statement} contradicted by"
    return f"{_strip_terminal_punctuation(fallback_query)} contradicted by"


def _extract_authoritative_domain(
    relevant_original_sources: list[TylerSource],
) -> str | None:
    """Pick the strongest known domain for authoritative-source targeting."""
    ranked_sources = sorted(
        relevant_original_sources,
        key=lambda source: (
            source.source_type not in {"official_docs", "academic"},
            -source.quality_score,
        ),
    )
    for source in ranked_sources:
        hostname = urlparse(source.url).hostname or ""
        hostname = hostname.removeprefix("www.")
        if hostname:
            return hostname
    return None


def _build_authoritative_verification_query(
    *,
    dispute: DisputeQueueEntry,
    claim_entries: list[ClaimLedgerEntry],
    relevant_original_sources: list[TylerSource],
    original_query: str,
) -> str:
    """Target the most authoritative source class available for the dispute."""
    domain = _extract_authoritative_domain(relevant_original_sources)
    topic = _strip_terminal_punctuation(dispute.description or "")
    if topic.lower().startswith("whether "):
        topic = _normalize_whether_predicate(topic[8:])
    if not topic and claim_entries:
        topic = _strip_terminal_punctuation(claim_entries[0].statement)
    if not topic:
        topic = _strip_terminal_punctuation(original_query)
    if domain:
        return f"site:{domain} {topic}"
    if dispute.type.value == "empirical":
        return f"{topic} official report primary study"
    return f"{topic} official documentation peer reviewed analysis"


def _build_dated_verification_query(authoritative_query: str) -> str:
    """Add an explicit current-year authoritative query for time-sensitive disputes."""
    current_year = str(datetime.now(timezone.utc).year)
    return f"{authoritative_query} {current_year}"


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
                "authoritative": 1.0,
                "reliable": 0.7,
                "unknown": 0.5,
                "unreliable": 0.3,
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
    bundle: EvidenceBundle,
    stage_1_result: DecompositionResult | None = None,
    stage_2_result: EvidencePackage | None = None,
    trace_id: str,
    max_disputes: int = 5,
    max_budget: float = 2.0,
) -> tuple[VerificationResult, list[VerificationWarning], int]:
    """Run Tyler's Stage 5 artifact without depending on deleted ledger projections."""
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
        raise ValueError(
            "Tyler Stage 5 requires a canonical Tyler Stage 2 EvidencePackage. "
            "Pass `stage_2_result` from the live pipeline or fixture artifacts "
            "instead of rebuilding it from the legacy EvidenceBundle."
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
        return empty, [], 0

    depth_cfg = get_depth_config()
    max_rounds = max(1, int(depth_cfg.get("arbitration_max_rounds", 1)))
    # Tyler V1 spec §Stage 5: "Max 3 queries per disputed claim"
    max_queries_per_dispute = int(get_budget("verification_max_queries_per_dispute"))
    budget_per_dispute = max_budget / len(actionable)
    llm_calls = 0
    warnings: list[VerificationWarning] = []
    all_additional_sources: list[AdditionalSource] = []
    investigated: list[ArbitrationAssessment] = []
    search_budget: dict[str, int] = {}
    rounds_used = 0

    for dispute in actionable:
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
                dispute=dispute,
                claim_entries=claim_entries,
                relevant_original_sources=relevant_original_sources,
                original_query=original_query,
                time_sensitivity=getattr(bundle.question, "time_sensitivity", "mixed"),
            )
            # Tyler V1: cap queries per dispute across all rounds
            used = search_budget.get(dispute.id, 0)
            remaining = max_queries_per_dispute - used
            if remaining <= 0:
                break
            queries = queries[:remaining]
            search_budget[dispute.id] = used + len(queries)

            new_sources, new_evidence, new_warnings = await _collect_fresh_evidence_for_dispute(
                dispute_id=dispute.id,
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
    return verification_result, warnings, llm_calls
