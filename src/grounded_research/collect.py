"""Evidence collection from a research question.

Takes a question string and automatically builds an EvidenceBundle by:
1. Generating diverse search queries via LLM
2. Searching via the shared web-search provider with recency filtering
3. Fetching and extracting full page content from top results (parallelized)
4. Extracting multiple evidence items per page
5. Structuring everything into an EvidenceBundle

Depth is configurable via config.yaml collection settings.

Uses open_web_retrieval for search and fetch.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import time
from typing import Literal
from urllib.parse import urlparse
from uuid import uuid4

from llm_client.observability import ToolCallResult, log_tool_call

from grounded_research.config import (
    get_depth_config,
    get_collection_ranking_config,
    get_fallback_models,
    get_model,
    get_phase_concurrency_config,
    load_config,
)
from grounded_research.models import (
    EvidenceBundle,
    EvidenceItem,
    ResearchQuestion,
    SourceRecord,
)
from grounded_research.runtime_policy import get_request_timeout
from grounded_research.tyler_v1_models import (
    DecompositionResult as TylerDecompositionResult,
    EvidenceLabel,
    EvidencePackage as TylerEvidencePackage,
    Finding,
    Source as TylerSource,
    StageSummary,
    SubQuestionEvidence,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

from grounded_research.evidence_utils import COLLECTION_FRESHNESS_MAP as _FRESHNESS_MAP, estimate_recency as _estimate_recency


def _tool_call_started(
    *,
    tool_name: str,
    operation: str,
    provider: str,
    target: str,
    trace_id: str,
    task: str,
    metrics: dict[str, object] | None = None,
) -> tuple[str, str, float]:
    """Log one shared started tool-call record and return timing state."""

    call_id = f"toolcall_{uuid4().hex}"
    started_at = datetime.now(timezone.utc).isoformat()
    started_monotonic = time.monotonic()
    log_tool_call(
        ToolCallResult(
            call_id=call_id,
            tool_name=tool_name,
            operation=operation,
            provider=provider,
            target=target,
            status="started",
            started_at=started_at,
            attempt=1,
            task=task,
            trace_id=trace_id,
            metrics=dict(metrics or {}),
        )
    )
    return call_id, started_at, started_monotonic


def _tool_call_finished(
    *,
    call_id: str,
    started_at: str,
    started_monotonic: float,
    tool_name: str,
    operation: str,
    provider: str,
    target: str,
    trace_id: str,
    task: str,
    status: Literal["succeeded", "failed"],
    metrics: dict[str, object] | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> None:
    """Log one shared final tool-call record."""

    log_tool_call(
        ToolCallResult(
            call_id=call_id,
            tool_name=tool_name,
            operation=operation,
            provider=provider,
            target=target,
            status=status,
            started_at=started_at,
            ended_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=max(0, int(round((time.monotonic() - started_monotonic) * 1000))),
            attempt=1,
            task=task,
            trace_id=trace_id,
            metrics=dict(metrics or {}),
            error_type=error_type,
            error_message=error_message,
        )
    )


def _extract_topic_anchors(question: str) -> list[str]:
    """Extract explicit topic anchors to keep generated queries on-topic.

    This is intentionally lightweight and conservative. It only returns anchors
    we can identify with high confidence from the original question text.
    """
    anchors: list[str] = []
    seen: set[str] = set()

    for phrase in re.findall(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", question):
        if phrase not in seen:
            anchors.append(phrase)
            seen.add(phrase)
        acronym = "".join(word[0].upper() for word in phrase.split())
        if len(acronym) >= 2 and acronym not in seen:
            anchors.append(acronym)
            seen.add(acronym)

    lowered = question.lower()
    for phrase in ("guaranteed income", "cash transfer", "cash transfers"):
        if phrase in lowered and phrase not in seen:
            anchors.append(phrase)
            seen.add(phrase)

    return anchors


def _anchor_queries(queries: list[str], topic_anchors: list[str]) -> list[str]:
    """Ensure generated queries retain the parent topic/intervention anchor."""
    if not topic_anchors:
        return queries

    anchored: list[str] = []
    seen: set[str] = set()
    primary_anchor = topic_anchors[0]
    lower_anchors = [anchor.lower() for anchor in topic_anchors]

    for query in queries:
        query_text = query.strip()
        if not query_text:
            continue
        if not any(anchor in query_text.lower() for anchor in lower_anchors):
            query_text = f"{primary_anchor} {query_text}"
        if query_text not in seen:
            anchored.append(query_text)
            seen.add(query_text)

    return anchored


def _score_search_result(result: dict, ranking_cfg: dict[str, object]) -> tuple[int, str]:
    """Score a raw search result before fetch.

    This is a mechanical budget-allocation policy, not a semantic source
    quality judgment. It exists to spend fetch budget on URLs that are more
    likely to contain high-value evidence before the later LLM quality pass.
    """
    url = str(result.get("url", ""))
    title = str(result.get("title", ""))
    description = str(result.get("description", ""))
    host = urlparse(url).netloc.lower()
    title_lower = title.lower()
    description_lower = description.lower()
    text = f"{title_lower} {description_lower}"
    score = 0
    reasons: list[str] = []

    preferred_domains = [
        str(pattern).lower()
        for pattern in ranking_cfg.get("preferred_domain_patterns", [])
    ]
    deprioritized_domains = [
        str(pattern).lower()
        for pattern in ranking_cfg.get("deprioritized_domain_patterns", [])
    ]
    preferred_terms = [
        str(term).lower()
        for term in ranking_cfg.get("preferred_title_terms", [])
    ]
    deprioritized_terms = [
        str(term).lower()
        for term in ranking_cfg.get("deprioritized_title_terms", [])
    ]

    if url.lower().endswith(".pdf"):
        score += int(ranking_cfg.get("pdf_bonus", 3))
        reasons.append("pdf")

    if any(pattern in host for pattern in preferred_domains):
        score += int(ranking_cfg.get("preferred_domain_bonus", 5))
        reasons.append("preferred_domain")

    if any(pattern in host for pattern in deprioritized_domains):
        score -= int(ranking_cfg.get("deprioritized_domain_penalty", 6))
        reasons.append("deprioritized_domain")

    preferred_hits = sum(1 for term in preferred_terms if term and term in text)
    if preferred_hits:
        score += preferred_hits * int(ranking_cfg.get("preferred_title_bonus", 2))
        reasons.append(f"preferred_terms={preferred_hits}")

    deprioritized_hits = sum(1 for term in deprioritized_terms if term and term in text)
    if deprioritized_hits:
        score -= deprioritized_hits * int(ranking_cfg.get("deprioritized_title_penalty", 3))
        reasons.append(f"deprioritized_terms={deprioritized_hits}")

    if description and len(description) >= 120:
        score += 1
        reasons.append("rich_snippet")

    quality_tier = str(result.get("prefetch_quality_tier", "")).lower()
    quality_bonus_map = ranking_cfg.get("quality_tier_bonus", {})
    if quality_tier and isinstance(quality_bonus_map, dict):
        score += int(quality_bonus_map.get(quality_tier, 0))
        reasons.append(f"quality={quality_tier}")

    return score, ",".join(reasons) or "neutral"


async def _extract_goal_driven_evidence(
    *,
    question: str,
    trace_id: str,
    source: SourceRecord,
    page_data: dict[str, object],
    sub_questions: list[dict[str, object]],
    sub_question_ids: list[str],
    max_items: int,
    max_chars: int,
) -> list[EvidenceItem]:
    """Extract multiple evidence items from one persisted page text.

    This depth-only path turns an already-fetched full page into a few distinct
    evidence items instead of relying solely on the generic notes/key-section
    pair. It reuses the existing EvidenceItem contract so downstream phases do
    not need a new boundary.
    """
    from llm_client import acall_llm_structured, render_prompt
    from pydantic import BaseModel, Field

    from grounded_research.tools.fetch_page import read_page

    file_path = str(page_data.get("file_path", "")).strip()
    if not file_path:
        raise ValueError("Depth extraction requires page_data.file_path")

    page_text = read_page(file_path, max_chars=max_chars).strip()
    if len(page_text) < 200:
        return []

    matched_sub_questions = [
        sq for sq in sub_questions
        if str(sq.get("id", "")) in sub_question_ids
    ]

    class ExtractedEvidenceItem(BaseModel):
        """LLM-facing extracted evidence payload."""

        content: str = Field(
            description="Concrete evidence-bearing passage or data point from the page.",
        )
        content_type: Literal["text", "data_point", "quotation", "summary"] = Field(
            description="Best-fit evidence type for the extracted item.",
        )
        relevance_note: str = Field(
            description="Why this item matters to the question or matched sub-questions.",
        )

    class ExtractionResult(BaseModel):
        """LLM output: extracted evidence items from one page."""

        items: list[ExtractedEvidenceItem] = Field(
            default_factory=list,
            description="Distinct evidence-bearing items from the page, capped by the prompt.",
        )

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "extract_evidence.yaml"),
        question=question,
        source_title=source.title,
        source_url=source.url,
        matched_sub_questions=matched_sub_questions,
        max_items=max_items,
        page_text=page_text,
    )

    result, _meta = await acall_llm_structured(
        get_model("evidence_extraction"),
        messages,
        response_model=ExtractionResult,
        task="evidence_extraction",
        trace_id=f"{trace_id}/extract/{source.id}",
        timeout=get_request_timeout("evidence_extraction"),
        max_budget=0.2,
        fallback_models=get_fallback_models("evidence_extraction"),
    )

    extracted: list[EvidenceItem] = []
    seen_signatures: set[str] = set()
    for item in result.items[:max_items]:
        content = item.content.strip()
        if len(content) < 40:
            continue
        signature = content[:160].lower()
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        extracted.append(EvidenceItem(
            source_id=source.id,
            content=content,
            content_type=item.content_type,
            relevance_note=item.relevance_note.strip(),
            extraction_method="llm",
            sub_question_ids=sub_question_ids,
        ))
    return extracted


def _fallback_page_evidence(
    *,
    source: SourceRecord,
    page_data: dict[str, object],
    question: str,
    sub_question_ids: list[str],
) -> list[EvidenceItem]:
    """Build the existing notes/key-section evidence pair.

    This remains the baseline path for standard mode and the explicit fallback
    when depth extraction fails or yields nothing useful.
    """
    evidence: list[EvidenceItem] = []
    char_count = int(page_data.get("char_count", 0) or 0)
    key_section = str(page_data.get("key_section", ""))
    if key_section and len(key_section) > 50:
        evidence.append(EvidenceItem(
            source_id=source.id,
            content=key_section,
            content_type="text",
            relevance_note=f"Key section ({char_count} chars total) for: {question[:50]}",
            extraction_method="llm",
            sub_question_ids=sub_question_ids,
        ))

    notes = str(page_data.get("notes", ""))
    if notes and len(notes) > 50 and notes != key_section[:len(notes)]:
        evidence.append(EvidenceItem(
            source_id=source.id,
            content=notes,
            content_type="summary",
            relevance_note=f"Page summary ({char_count} chars total)",
            extraction_method="llm",
            sub_question_ids=sub_question_ids,
        ))
    return evidence


async def generate_search_queries(
    question: str,
    trace_id: str,
    max_budget: float = 0.5,
    num_queries: int = 10,
    time_sensitivity: str = "mixed",
    sub_questions: list[dict] | None = None,
) -> tuple[list[str], dict[str, str]]:
    """Generate diverse search queries for a research question via LLM.

    If sub_questions are provided (from Tyler Stage 1 decomposition), generates
    queries per sub-question for focused evidence collection. Otherwise
    falls back to monolithic question-level query generation.

    Returns (queries, query_to_sq_id) where query_to_sq_id maps each query
    string to the sub-question ID that generated it (empty dict if no sub-questions).
    """
    from llm_client import acall_llm_structured, render_prompt
    from pydantic import BaseModel, Field

    class SearchQueries(BaseModel):
        """LLM output: search queries for evidence collection."""
        queries: list[str] = Field(description="Diverse search queries to gather evidence.")

    recency_note = ""
    if time_sensitivity == "time_sensitive":
        recency_note = (
            f"This is a time-sensitive topic. Include the current year ({datetime.now().year}) "
            "in at least half the queries to find recent information."
        )

    model = get_model("analyst")
    topic_anchors = _extract_topic_anchors(question)

    if sub_questions:
        # Generate queries per sub-question for focused coverage
        all_queries: list[str] = []
        query_to_sq: dict[str, str] = {}
        queries_per_sq = max(3, num_queries // len(sub_questions))

        # Generate queries for all sub-questions in parallel
        async def _gen_sq_queries(sq):
            sq_id = sq.get("id", "sq")
            messages = render_prompt(
                str(_PROJECT_ROOT / "prompts" / "query_generation.yaml"),
                mode="sub_question",
                question=question,
                topic_anchors=topic_anchors,
                sub_question=sq,
                recency_note=recency_note,
                query_count=queries_per_sq,
            )
            sq_result, _meta = await acall_llm_structured(
                model,
                messages,
                response_model=SearchQueries,
                task="query_generation",
                trace_id=f"{trace_id}/queries/{sq_id}",
                timeout=get_request_timeout("query_generation"),
                max_budget=max_budget / len(sub_questions),
                fallback_models=get_fallback_models("analyst"),
            )
            return sq_id, sq_result.queries

        sq_results = await asyncio.gather(*[_gen_sq_queries(sq) for sq in sub_questions])
        for sq_id, queries in sq_results:
            anchored_queries = _anchor_queries(queries, topic_anchors)
            for q in anchored_queries:
                query_to_sq[q] = sq_id
            all_queries.extend(anchored_queries)

        return all_queries, query_to_sq

    # Fallback: monolithic question-level generation
    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "query_generation.yaml"),
        mode="question",
        question=question,
        topic_anchors=topic_anchors,
        recency_note=recency_note,
        query_count=num_queries,
    )
    result, _meta = await acall_llm_structured(
        model,
        messages,
        response_model=SearchQueries,
        task="query_generation",
        trace_id=f"{trace_id}/queries",
        timeout=get_request_timeout("query_generation"),
        max_budget=max_budget,
        fallback_models=get_fallback_models("analyst"),
    )
    return result.queries, {}


async def generate_search_queries_tyler_v1(
    stage_1_result: TylerDecompositionResult,
    trace_id: str,
    max_budget: float = 0.5,
) -> tuple[list[str], dict[str, str], dict[str, int]]:
    """Generate Tyler-native Stage 2 query variants per sub-question.

    Tyler V1 spec §Stage 2: "Generate 3-5 query variants per sub-question
    (formal/colloquial, academic/practitioner, broad/narrow) — string
    templates, not a model call."

    No LLM call. Deterministic string templates only.
    """
    query_to_sq: dict[str, str] = {}
    queries_per_sq: dict[str, int] = {}
    all_queries: list[str] = []

    for sub_question in stage_1_result.sub_questions:
        q = sub_question.question.strip().rstrip("?").strip()
        guidance = (sub_question.search_guidance or "").strip()

        generated: list[str] = []
        seen: set[str] = set()

        def _add(query: str) -> None:
            query = query.strip()
            if query and query not in seen:
                generated.append(query)
                seen.add(query)

        # 1. KEYWORD: extract core topic words
        _add(q)

        # 2. FORMAL/ACADEMIC: add academic signal
        _add(f"{q} systematic review OR meta-analysis OR study")

        # 3. PRACTITIONER: add practitioner signals
        _add(f"{q} lessons learned OR we found that OR case study")

        # 4. CONTRARIAN/FALSIFICATION: Tyler counterfactual pattern
        _add(f"{q} limitations OR contradicted OR failure OR criticism")

        # 5. If search_guidance provides extra keywords, use them
        if guidance and guidance.lower() != q.lower():
            _add(f"{q} {guidance}")

        # Tyler V1 §Stage 2: "hard cap: 4 queries per sub-question (named constant)"
        _MAX_QUERIES_PER_SUB_QUESTION = 4
        generated = generated[:_MAX_QUERIES_PER_SUB_QUESTION]

        queries_per_sq[sub_question.id] = len(generated)
        for query in generated:
            query_to_sq[query] = sub_question.id
            all_queries.append(query)

    return all_queries, query_to_sq, queries_per_sq


def _current_source_type_to_tyler_source_type(source_type: str) -> str:
    """Project current source taxonomy into Tyler's Stage 2 source_type enum."""
    mapping = {
        "government_db": "official_docs",
        "primary_document": "official_docs",
        "academic": "academic",
        "news": "news",
        "web_search": "practitioner_report",
        "social_media": "forum",
        "platform_transparency": "official_docs",
    }
    return mapping.get(source_type, "blog")


def _current_quality_tier_to_tyler_score(quality_tier: str) -> float:
    """Map quality tiers to Tyler V1 numeric scores.

    Tyler spec: "1.0 official docs → 0.3 generic blog. Unknown = 0.5."
    """
    return {
        "authoritative": 1.0,
        "reliable": 0.7,
        "unknown": 0.5,
        "unreliable": 0.3,
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


async def build_tyler_evidence_package(
    bundle: EvidenceBundle,
    stage_1_result: TylerDecompositionResult,
    trace_id: str,
    *,
    query_counts_by_sub_question: dict[str, int] | None = None,
    max_budget: float = 0.5,
) -> TylerEvidencePackage:
    """Build Tyler's Stage 2 artifact from the collected bundle.

    Retrieval and page persistence remain mechanical. This function is the live
    semantic Stage 2 surface: it normalizes evidence into Tyler's grouped
    `EvidencePackage` contract using Tyler's finding-extraction prompt.
    """
    from llm_client import acall_llm_structured, render_prompt
    from pydantic import BaseModel, Field

    class FindingExtractionResult(BaseModel):
        """LLM-facing Tyler finding extraction payload."""

        findings: list[Finding] = Field(
            default_factory=list,
            description="Atomic findings extracted from this source for the given sub-question.",
        )

    source_by_id = {source.id: source for source in bundle.sources}
    valid_sub_question_ids = {sub_question.id for sub_question in stage_1_result.sub_questions}
    grouped_items: dict[tuple[str, str], list[EvidenceItem]] = {}
    for item in bundle.evidence:
        target_sub_question_ids = item.sub_question_ids or [stage_1_result.sub_questions[0].id]
        unknown_sub_question_ids = sorted(
            sub_question_id
            for sub_question_id in target_sub_question_ids
            if sub_question_id not in valid_sub_question_ids
        )
        if unknown_sub_question_ids:
            raise ValueError(
                "Tyler Stage 2 requires Tyler Stage 1 sub-question IDs in EvidenceItem.sub_question_ids. "
                f"Unknown IDs: {', '.join(unknown_sub_question_ids)}"
            )
        for sub_question_id in target_sub_question_ids:
            grouped_items.setdefault((sub_question_id, item.source_id), []).append(item)

    sub_question_evidence: list[SubQuestionEvidence] = []
    query_counts = dict(query_counts_by_sub_question or {})

    for sub_question in stage_1_result.sub_questions:
        stage_sources: list[TylerSource] = []
        supporting_source_ids = [
            source_id
            for (sub_question_id, source_id) in grouped_items
            if sub_question_id == sub_question.id and source_id in source_by_id
        ]
        for source_id in supporting_source_ids:
            source = source_by_id[source_id]
            items = grouped_items[(sub_question.id, source_id)]
            source_content = "\n\n".join(
                dict.fromkeys(item.content.strip() for item in items if item.content.strip())
            )[:12000]
            messages = render_prompt(
                str(_PROJECT_ROOT / "prompts" / "tyler_v1_extract_findings.yaml"),
                original_query=bundle.question.text,
                sub_question_id=sub_question.id,
                sub_question_text=sub_question.question,
                source_title=source.title,
                source_url=source.url,
                source_type=_current_source_type_to_tyler_source_type(source.source_type),
                source_content=source_content,
                response_schema_json=FindingExtractionResult.model_json_schema(),
            )
            result, _meta = await acall_llm_structured(
                get_model("evidence_extraction"),
                messages,
                response_model=FindingExtractionResult,
                task="finding_extraction_tyler_v1",
                trace_id=f"{trace_id}/stage2/{sub_question.id}/{source.id}",
                timeout=get_request_timeout("evidence_extraction"),
                max_budget=max_budget / max(1, len(grouped_items)),
                fallback_models=get_fallback_models("evidence_extraction"),
            )
            findings = list(result.findings)
            if not findings:
                findings = [
                    Finding(
                        finding=item.content,
                        evidence_label=_current_source_to_evidence_label(source.source_type),
                        original_quote=item.content if item.content_type in {"quotation", "data_point"} else None,
                    )
                    for item in items[:3]
                ]
            stage_sources.append(
                TylerSource(
                    id=source.id,
                    url=source.url,
                    title=source.title,
                    source_type=_current_source_type_to_tyler_source_type(source.source_type),
                    quality_score=_current_quality_tier_to_tyler_score(source.quality_tier),
                    publication_date=source.published_at.date().isoformat() if source.published_at else None,
                    retrieval_date=source.retrieved_at.date().isoformat(),
                    key_findings=findings,
                )
            )

        high_quality_count = sum(1 for source in stage_sources if source.quality_score >= 0.75)
        meets_sufficiency = high_quality_count >= 2
        gap_description = None
        if not meets_sufficiency:
            gap_description = (
                f"Only {high_quality_count} high-quality independent source(s) were found "
                f"for {sub_question.id}."
            )
        sub_question_evidence.append(
            SubQuestionEvidence(
                sub_question_id=sub_question.id,
                sources=stage_sources,
                meets_sufficiency=meets_sufficiency,
                gap_description=gap_description,
            )
        )
        query_counts.setdefault(sub_question.id, 0)

    return TylerEvidencePackage(
        sub_question_evidence=sub_question_evidence,
        total_queries_used=sum(query_counts.values()),
        queries_per_sub_question=query_counts,
        stage_summary=StageSummary(
            stage_name="Stage 2: Broad Retrieval & Evidence Normalization",
            goal="Retrieve broad evidence and normalize it into Tyler's grouped Stage 2 contract.",
            key_findings=[
                f"{len(bundle.sources)} fetched sources were normalized into Tyler Stage 2",
                f"{len(bundle.evidence)} compatibility evidence items fed Tyler finding extraction",
                f"{sum(len(sqe.sources) for sqe in sub_question_evidence)} source-group assignments landed in Stage 2",
            ],
            decisions_made=[
                "Used Tyler query diversification output for sub-question search coverage when Stage 1 was Tyler-native",
                "Built Tyler findings from the collected source evidence while keeping the flat bundle as compatibility substrate",
            ],
            outcome=f"{len(sub_question_evidence)} Tyler sub-question evidence groups",
            reasoning="Stage 2 now treats Tyler's EvidencePackage as the live semantic artifact while preserving the flat EvidenceBundle as the retrieval substrate.",
        ),
    )


async def collect_evidence_tyler_v1(
    stage_1_result: TylerDecompositionResult,
    trace_id: str,
    *,
    max_sources: int = 20,
    max_budget: float = 1.0,
    time_sensitivity: str = "mixed",
    scope_notes: str = "",
    num_queries: int = 10,
    results_per_query: int = 10,
) -> tuple[TylerEvidencePackage, EvidenceBundle]:
    """Run the Stage 2 collection path and return Tyler + compatibility artifacts."""
    bundle, query_counts = await collect_evidence(
        stage_1_result.core_question,
        trace_id,
        max_sources=max_sources,
        max_budget=max_budget,
        time_sensitivity=time_sensitivity,
        scope_notes=scope_notes,
        num_queries=num_queries,
        results_per_query=results_per_query,
        sub_questions=[sub_question.model_dump(mode="json") for sub_question in stage_1_result.sub_questions],
        tyler_stage_1_result=stage_1_result,
        return_query_counts=True,
    )
    stage_2_result = await build_tyler_evidence_package(
        bundle,
        stage_1_result,
        trace_id=f"{trace_id}/stage2_build",
        query_counts_by_sub_question=query_counts,
        max_budget=max_budget * 0.15,
    )
    return stage_2_result, bundle


async def collect_evidence(
    question: str,
    trace_id: str,
    max_sources: int = 20,
    max_budget: float = 1.0,
    time_sensitivity: str = "mixed",
    scope_notes: str = "",
    num_queries: int = 10,
    results_per_query: int = 10,
    sub_questions: list[dict] | None = None,
    tyler_stage_1_result: TylerDecompositionResult | None = None,
    return_query_counts: bool = False,
) -> EvidenceBundle | tuple[EvidenceBundle, dict[str, int]]:
    """Collect evidence for a research question from web sources.

    If sub_questions are provided (from Tyler Stage 1 decomposition), generates
    focused search queries per sub-question. Otherwise uses monolithic
    question-level queries.

    Searches the web, fetches top results with full page content
    extraction, and structures everything into an EvidenceBundle.

    Depth is controlled by num_queries × results_per_query for search
    breadth, and max_sources for how many pages to actually fetch.
    """
    from grounded_research.tools.web_search import search_web
    from grounded_research.tools.fetch_page import fetch_page, set_pages_dir

    config = load_config()
    depth_cfg = get_depth_config()
    phase_cfg = get_phase_concurrency_config()
    collection_cfg = config.get("collection", {})
    # Only use collection config as defaults if caller didn't override
    if num_queries == 10:  # default parameter value
        num_queries = collection_cfg.get("num_queries", num_queries)
    results_per_query = collection_cfg.get("results_per_query", results_per_query)
    if max_sources == 20:  # default parameter value
        max_sources = collection_cfg.get("max_sources", max_sources)

    # Set up pages directory for full-text caching
    pages_dir = _PROJECT_ROOT / "output" / "pages"
    set_pages_dir(pages_dir)

    research_q = ResearchQuestion(
        text=question,
        time_sensitivity=time_sensitivity,
        scope_notes=scope_notes,
    )

    # Determine freshness filter based on time sensitivity
    freshness = _FRESHNESS_MAP.get(time_sensitivity, "py")

    sq_label = f" across {len(sub_questions)} sub-questions" if sub_questions else ""
    print(f"  Generating search queries{sq_label}...")
    query_counts_by_sub_question: dict[str, int] = {}
    if tyler_stage_1_result is not None:
        queries, query_to_sq, query_counts_by_sub_question = await generate_search_queries_tyler_v1(
            tyler_stage_1_result,
            trace_id,
            max_budget=max_budget * 0.1,
        )
    else:
        queries, query_to_sq = await generate_search_queries(
            question, trace_id,
            max_budget=max_budget * 0.1,
            num_queries=num_queries,
            time_sensitivity=time_sensitivity,
            sub_questions=sub_questions,
        )
    print(f"  Generated {len(queries)} queries (freshness: {freshness})")

    # Search all queries in parallel, then deduplicate by URL
    url_sq_ids: dict[str, set[str]] = {}  # url → all sub-question IDs that found it

    async def _search_one(q: str) -> list[dict]:
        """Search one query, return results with query tag."""
        results = []
        try:
            raw = await search_web(
                q,
                count=results_per_query,
                freshness=freshness,
                trace_id=trace_id,
                task="collection.search",
            )
            data = json.loads(raw)
            for r in data.get("results", []):
                r["search_query"] = q
                results.append(r)

            if time_sensitivity == "time_sensitive":
                raw_unfiltered = await search_web(
                    q,
                    count=3,
                    freshness="none",
                    trace_id=trace_id,
                    task="collection.search",
                )
                data_unfiltered = json.loads(raw_unfiltered)
                for r in data_unfiltered.get("results", []):
                    r["search_query"] = q
                    r["recency_note"] = "unfiltered_complement"
                    results.append(r)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Search failed for '%s': %s", q[:50], e)
        return results

    all_raw_results = await asyncio.gather(*[_search_one(q) for q in queries])

    # Flatten and deduplicate
    all_search_results: list[dict] = []
    seen_urls: set[str] = set()
    for results in all_raw_results:
        for r in results:
            url = r.get("url", "")
            if not url:
                continue
            sq_id = query_to_sq.get(r.get("search_query", ""))
            if sq_id:
                url_sq_ids.setdefault(url, set()).add(sq_id)
            if url not in seen_urls:
                seen_urls.add(url)
                all_search_results.append(r)

    print(f"  Found {len(all_search_results)} unique URLs across {len(queries)} queries")

    # Score candidate source quality before fetch so fetch budget is spent on
    # stronger candidates, not just the first diverse URLs returned by search.
    if all_search_results:
        candidate_sources: list[SourceRecord] = []
        candidate_urls: list[str] = []
        for result in all_search_results:
            candidate_sources.append(
                SourceRecord(
                    url=result["url"],
                    title=result.get("title", ""),
                    source_type="web_search",
                    quality_tier="reliable",
                    retrieved_at=datetime.now(timezone.utc),
                    recency_score=_estimate_recency(result.get("age", "")),
                )
            )
            candidate_urls.append(result["url"])

        candidate_bundle = EvidenceBundle(
            question=research_q,
            sources=candidate_sources,
            evidence=[],
            gaps=[],
            imported_from="web_search_candidates",
        )
        from grounded_research.source_quality import score_source_quality

        print("  Scoring candidate source quality before fetch...")
        await score_source_quality(candidate_bundle, f"{trace_id}/candidate_pool", max_budget=max_budget * 0.05)
        candidate_quality_by_url = {
            source.url: source.quality_tier for source in candidate_bundle.sources
        }
        for result in all_search_results:
            result["prefetch_quality_tier"] = candidate_quality_by_url.get(
                result["url"], "reliable"
            )

    # Select top results — prefer diversity across queries
    selected = _select_diverse(all_search_results, max_sources)

    # Build source records from selected results
    sources: list[SourceRecord] = []
    evidence: list[EvidenceItem] = []
    gaps: list[str] = []

    source_map: dict[str, SourceRecord] = {}
    source_sq_ids_map: dict[str, list[str]] = {}  # url → all matched sub-question IDs
    for result in selected:
        url = result["url"]
        title = result.get("title", "")
        description = result.get("description", "")
        age = result.get("age", "")
        recency_score = _estimate_recency(age)

        source = SourceRecord(
            url=url,
            title=title,
            source_type="web_search",
            quality_tier=result.get("prefetch_quality_tier", "reliable"),
            retrieved_at=datetime.now(timezone.utc),
            recency_score=recency_score,
        )
        sources.append(source)
        source_map[url] = source

        # Preserve every matched sub-question tag so coverage is not undercounted.
        sq_ids = sorted(url_sq_ids.get(url, set()))
        source_sq_ids_map[url] = sq_ids

        # Add search snippet as evidence
        if description and len(description) > 30:
            evidence.append(EvidenceItem(
                source_id=source.id,
                content=description,
                content_type="summary",
                relevance_note=f"Search snippet for: {result.get('search_query', '')}",
                extraction_method="upstream",
                sub_question_ids=sq_ids,
            ))

    # Fetch page content in parallel (with Jina Reader fallback for 403s)
    async def _fetch_one(url: str, idx: int) -> tuple[str, dict | None]:
        """Fetch one page, return (url, page_data) or (url, None) on failure."""
        call_id, started_at, started_monotonic = _tool_call_started(
            tool_name="grounded_research",
            operation="fetch_page",
            provider="local_fetch_page",
            target=url,
            trace_id=trace_id,
            task="collection.fetch",
        )
        try:
            print(f"  Fetching [{idx+1}/{len(selected)}] {url[:60]}...")
            raw_page = await fetch_page(url, question=question)
            page_data = json.loads(raw_page)

            if page_data.get("error") and "403" in str(page_data.get("error", "")):
                _tool_call_finished(
                    call_id=call_id,
                    started_at=started_at,
                    started_monotonic=started_monotonic,
                    tool_name="grounded_research",
                    operation="fetch_page",
                    provider="local_fetch_page",
                    target=url,
                    trace_id=trace_id,
                    task="collection.fetch",
                    status="failed",
                    metrics={"fallback": "jina_reader"},
                    error_type="HTTP403Fallback",
                    error_message=str(page_data.get("error", "")),
                )
                fallback_call_id, fallback_started_at, fallback_started_monotonic = _tool_call_started(
                    tool_name="grounded_research",
                    operation="fetch_page",
                    provider="jina_reader",
                    target=url,
                    trace_id=trace_id,
                    task="collection.fetch",
                )
                from grounded_research.tools.jina_reader import fetch_page_jina
                print(f"    → 403 blocked, retrying via Jina Reader...")
                raw_page = await fetch_page_jina(url, question=question)
                page_data = json.loads(raw_page)
                if page_data.get("error"):
                    _tool_call_finished(
                        call_id=fallback_call_id,
                        started_at=fallback_started_at,
                        started_monotonic=fallback_started_monotonic,
                        tool_name="grounded_research",
                        operation="fetch_page",
                        provider="jina_reader",
                        target=url,
                        trace_id=trace_id,
                        task="collection.fetch",
                        status="failed",
                        error_type="JinaReaderError",
                        error_message=str(page_data.get("error", "")),
                    )
                else:
                    _tool_call_finished(
                        call_id=fallback_call_id,
                        started_at=fallback_started_at,
                        started_monotonic=fallback_started_monotonic,
                        tool_name="grounded_research",
                        operation="fetch_page",
                        provider="jina_reader",
                        target=url,
                        trace_id=trace_id,
                        task="collection.fetch",
                        status="succeeded",
                        metrics={
                            "content_type": str(page_data.get("content_type", "")),
                            "char_count": int(page_data.get("char_count", 0) or 0),
                            "fetched_via": str(page_data.get("fetched_via", "jina_reader")),
                        },
                    )
                    return url, page_data
                if page_data.get("error"):
                    return url, None

            if page_data.get("error"):
                _tool_call_finished(
                    call_id=call_id,
                    started_at=started_at,
                    started_monotonic=started_monotonic,
                    tool_name="grounded_research",
                    operation="fetch_page",
                    provider="local_fetch_page",
                    target=url,
                    trace_id=trace_id,
                    task="collection.fetch",
                    status="failed",
                    error_type="FetchPageError",
                    error_message=str(page_data.get("error", "")),
                )
                return url, None
            _tool_call_finished(
                call_id=call_id,
                started_at=started_at,
                started_monotonic=started_monotonic,
                tool_name="grounded_research",
                operation="fetch_page",
                provider="local_fetch_page",
                target=url,
                trace_id=trace_id,
                task="collection.fetch",
                status="succeeded",
                metrics={
                    "content_type": str(page_data.get("content_type", "")),
                    "char_count": int(page_data.get("char_count", 0) or 0),
                },
            )
            return url, page_data
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Fetch failed for %s: %s", url, e)
            _tool_call_finished(
                call_id=call_id,
                started_at=started_at,
                started_monotonic=started_monotonic,
                tool_name="grounded_research",
                operation="fetch_page",
                provider="local_fetch_page",
                target=url,
                trace_id=trace_id,
                task="collection.fetch",
                status="failed",
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return url, None

    # Run all fetches concurrently
    fetch_tasks = [_fetch_one(r["url"], i) for i, r in enumerate(selected)]
    fetch_results = await asyncio.gather(*fetch_tasks)

    depth_extraction_enabled = bool(depth_cfg.get("evidence_extraction_enabled", False))
    extraction_max_sources = int(depth_cfg.get("evidence_extraction_max_sources", 0))
    extraction_max_items = int(depth_cfg.get("evidence_extraction_items_per_source", 0))
    extraction_max_chars = int(depth_cfg.get("evidence_extraction_max_chars", 0))
    extraction_max_concurrency = int(phase_cfg.get("evidence_extraction_max_concurrency", 1))
    sub_question_list = sub_questions or []

    extraction_candidates: list[tuple[str, dict[str, object]]] = []
    extracted_evidence_by_url: dict[str, list[EvidenceItem]] = {}
    extraction_errors_by_url: dict[str, str] = {}

    if depth_extraction_enabled and extraction_max_sources > 0 and extraction_max_items > 0 and extraction_max_chars > 0:
        for url, page_data in fetch_results:
            if page_data is None:
                continue
            if len(extraction_candidates) >= extraction_max_sources:
                break
            if not str(page_data.get("file_path", "")).strip():
                continue
            extraction_candidates.append((url, page_data))

        if extraction_candidates:
            semaphore = asyncio.Semaphore(max(1, extraction_max_concurrency))

            async def _extract_one(url: str, page_data: dict[str, object]) -> tuple[str, list[EvidenceItem], str | None]:
                async with semaphore:
                    try:
                        return (
                            url,
                            await _extract_goal_driven_evidence(
                                question=question,
                                trace_id=trace_id,
                                source=source_map[url],
                                page_data=page_data,
                                sub_questions=sub_question_list,
                                sub_question_ids=source_sq_ids_map.get(url, []),
                                max_items=extraction_max_items,
                                max_chars=extraction_max_chars,
                            ),
                            None,
                        )
                    except Exception as exc:
                        return url, [], f"{type(exc).__name__}: {exc}"

            extracted_results = await asyncio.gather(
                *[_extract_one(url, page_data) for url, page_data in extraction_candidates]
            )
            for url, items, error in extracted_results:
                if error is not None:
                    extraction_errors_by_url[url] = error
                if items:
                    extracted_evidence_by_url[url] = items

    for url, page_data in fetch_results:
        source = source_map[url]
        sq_ids = source_sq_ids_map.get(url, [])
        if page_data is None:
            gaps.append(f"Failed to fetch {url}")
            continue
        extraction_error = extraction_errors_by_url.get(url)
        if extraction_error is not None:
            gaps.append(f"Depth evidence extraction failed for {url}: {extraction_error}")

        extracted_items = extracted_evidence_by_url.get(url, [])
        if extracted_items:
            evidence.extend(extracted_items)
            continue

        evidence.extend(_fallback_page_evidence(
            source=source,
            page_data=page_data,
            question=question,
            sub_question_ids=sq_ids,
        ))

    print(f"  Collected {len(sources)} sources, {len(evidence)} evidence items, {len(gaps)} gaps")

    bundle = EvidenceBundle(
        question=research_q,
        sources=sources,
        evidence=evidence,
        gaps=gaps,
        imported_from="web_search",
    )

    tier_counts = {}
    for s in bundle.sources:
        tier_counts[s.quality_tier] = tier_counts.get(s.quality_tier, 0) + 1
    print(f"  Source quality: {tier_counts}")

    if return_query_counts:
        return bundle, query_counts_by_sub_question
    return bundle


def _select_diverse(results: list[dict], max_items: int) -> list[dict]:
    """Select results with diversity across search queries.

    Within each query bucket, results are mechanically ranked before the
    round-robin pass so weak domains do not crowd out stronger sources before
    fetch. Diversity across queries is still preserved.
    """
    ranking_cfg = get_collection_ranking_config()
    by_query: dict[str, list[dict]] = {}
    for r in results:
        q = r.get("search_query", "")
        by_query.setdefault(q, []).append(r)

    for q, items in by_query.items():
        items.sort(
            key=lambda item: _score_search_result(item, ranking_cfg),
            reverse=True,
        )

    selected: list[dict] = []
    seen: set[str] = set()
    max_rounds = max_items

    for round_num in range(max_rounds):
        added_this_round = False
        for q, items in by_query.items():
            if round_num < len(items):
                url = items[round_num]["url"]
                if url not in seen:
                    seen.add(url)
                    selected.append(items[round_num])
                    added_this_round = True
                    if len(selected) >= max_items:
                        return selected
        if not added_this_round:
            break

    return selected
