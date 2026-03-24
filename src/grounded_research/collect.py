"""Evidence collection from a research question.

Takes a question string and automatically builds an EvidenceBundle by:
1. Generating diverse search queries via LLM
2. Searching via Brave Search API with recency filtering
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

from grounded_research.config import get_fallback_models, get_model, load_config
from grounded_research.models import (
    EvidenceBundle,
    EvidenceItem,
    ResearchQuestion,
    SourceRecord,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

from grounded_research.evidence_utils import COLLECTION_FRESHNESS_MAP as _FRESHNESS_MAP, estimate_recency as _estimate_recency


async def generate_search_queries(
    question: str,
    trace_id: str,
    max_budget: float = 0.5,
    num_queries: int = 10,
    time_sensitivity: str = "mixed",
    sub_questions: list[dict] | None = None,
) -> tuple[list[str], dict[str, str]]:
    """Generate diverse search queries for a research question via LLM.

    If sub_questions are provided (from QuestionDecomposition), generates
    queries per sub-question for focused evidence collection. Otherwise
    falls back to monolithic question-level query generation.

    Returns (queries, query_to_sq_id) where query_to_sq_id maps each query
    string to the sub-question ID that generated it (empty dict if no sub-questions).
    """
    from llm_client import acall_llm_structured
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

    if sub_questions:
        # Generate queries per sub-question for focused coverage
        all_queries: list[str] = []
        query_to_sq: dict[str, str] = {}
        queries_per_sq = max(3, num_queries // len(sub_questions))

        # Generate queries for all sub-questions in parallel
        async def _gen_sq_queries(sq):
            sq_id = sq.get("id", "sq")
            sq_result, _meta = await acall_llm_structured(
                model,
                [
                    {"role": "system", "content": (
                        "Generate diverse search queries for a specific research sub-question. "
                        "Include queries that would find:\n"
                        "(1) direct evidence answering the sub-question\n"
                        "(2) evidence that would DISPROVE the expected answer\n"
                        "(3) concrete data, statistics, or primary sources\n"
                        "(4) lists or surveys of specific programs, studies, benchmarks, or pilots\n"
                        "(5) named studies with sample sizes and quantitative findings\n"
                        f"\n{recency_note}\n"
                        f"Generate exactly {queries_per_sq} queries."
                    )},
                    {"role": "user", "content": (
                        f"Sub-question [{sq['type']}]: {sq['text']}\n"
                        f"Falsification target: {sq['falsification_target']}"
                    )},
                ],
                response_model=SearchQueries,
                task="query_generation",
                trace_id=f"{trace_id}/queries/{sq_id}",
                max_budget=max_budget / len(sub_questions),
                fallback_models=get_fallback_models("analyst"),
            )
            return sq_id, sq_result.queries

        sq_results = await asyncio.gather(*[_gen_sq_queries(sq) for sq in sub_questions])
        for sq_id, queries in sq_results:
            for q in queries:
                query_to_sq[q] = sq_id
            all_queries.extend(queries)

        return all_queries, query_to_sq

    # Fallback: monolithic question-level generation
    result, _meta = await acall_llm_structured(
        model,
        [
            {"role": "system", "content": (
                "Generate diverse search queries to gather comprehensive evidence "
                "for answering a research question. Include queries that would find:\n"
                "(1) arguments FOR the main thesis\n"
                "(2) arguments AGAINST or alternatives\n"
                "(3) concrete data, benchmarks, or performance comparisons\n"
                "(4) real-world experience reports and case studies\n"
                "(5) expert opinions, reviews, or analyses\n"
                "(6) limitations, criticisms, and failure modes\n"
                "(7) comparison with competing approaches\n"
                "(8) long-term maintainability and scaling evidence\n"
                f"\n{recency_note}\n"
                f"Generate exactly {num_queries} queries."
            )},
            {"role": "user", "content": question},
        ],
        response_model=SearchQueries,
        task="query_generation",
        trace_id=f"{trace_id}/queries",
        max_budget=max_budget,
        fallback_models=get_fallback_models("analyst"),
    )
    return result.queries, {}


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
) -> EvidenceBundle:
    """Collect evidence for a research question from web sources.

    If sub_questions are provided (from QuestionDecomposition), generates
    focused search queries per sub-question. Otherwise uses monolithic
    question-level queries.

    Searches the web, fetches top results with full page content
    extraction, and structures everything into an EvidenceBundle.

    Depth is controlled by num_queries × results_per_query for search
    breadth, and max_sources for how many pages to actually fetch.
    """
    from grounded_research.tools.brave_search import search_web
    from grounded_research.tools.fetch_page import fetch_page, set_pages_dir

    config = load_config()
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
            raw = await search_web(q, count=results_per_query, freshness=freshness)
            data = json.loads(raw)
            for r in data.get("results", []):
                r["search_query"] = q
                results.append(r)

            if time_sensitivity == "time_sensitive":
                raw_unfiltered = await search_web(q, count=3, freshness="none")
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

    # Select top results — prefer diversity across queries
    selected = _select_diverse(all_search_results, max_sources)

    # Build source records from selected results
    sources: list[SourceRecord] = []
    evidence: list[EvidenceItem] = []
    gaps: list[str] = []

    source_map: dict[str, SourceRecord] = {}
    source_sq_map: dict[str, str | None] = {}  # url → sub_question_id
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
            quality_tier="reliable",
            retrieved_at=datetime.now(timezone.utc),
            recency_score=recency_score,
        )
        sources.append(source)
        source_map[url] = source

        # Use the richest sub-question mapping (all queries that found this URL)
        sq_ids = url_sq_ids.get(url, set())
        source_sq_map[url] = next(iter(sq_ids)) if sq_ids else None
        sq_id = query_to_sq.get(result.get("search_query", ""))

        # Add search snippet as evidence
        if description and len(description) > 30:
            evidence.append(EvidenceItem(
                source_id=source.id,
                content=description,
                content_type="summary",
                relevance_note=f"Search snippet for: {result.get('search_query', '')}",
                extraction_method="upstream",
                sub_question_id=sq_id,
            ))

    # Fetch page content in parallel (with Jina Reader fallback for 403s)
    async def _fetch_one(url: str, idx: int) -> tuple[str, dict | None]:
        """Fetch one page, return (url, page_data) or (url, None) on failure."""
        try:
            print(f"  Fetching [{idx+1}/{len(selected)}] {url[:60]}...")
            raw_page = await fetch_page(url, question=question)
            page_data = json.loads(raw_page)

            if page_data.get("error") and "403" in str(page_data.get("error", "")):
                from grounded_research.tools.jina_reader import fetch_page_jina
                print(f"    → 403 blocked, retrying via Jina Reader...")
                raw_page = await fetch_page_jina(url, question=question)
                page_data = json.loads(raw_page)

            if page_data.get("error"):
                return url, None
            return url, page_data
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Fetch failed for %s: %s", url, e)
            return url, None

    # Run all fetches concurrently
    fetch_tasks = [_fetch_one(r["url"], i) for i, r in enumerate(selected)]
    fetch_results = await asyncio.gather(*fetch_tasks)

    for url, page_data in fetch_results:
        source = source_map[url]
        sq_id = source_sq_map.get(url)
        if page_data is None:
            gaps.append(f"Failed to fetch {url}")
            continue

        char_count = page_data.get("char_count", 0)

        key_section = page_data.get("key_section", "")
        if key_section and len(key_section) > 50:
            evidence.append(EvidenceItem(
                source_id=source.id,
                content=key_section,
                content_type="text",
                relevance_note=f"Key section ({char_count} chars total) for: {question[:50]}",
                extraction_method="llm",
                sub_question_id=sq_id,
            ))

        notes = page_data.get("notes", "")
        if notes and len(notes) > 50 and notes != key_section[:len(notes)]:
            evidence.append(EvidenceItem(
                source_id=source.id,
                content=notes,
                content_type="summary",
                relevance_note=f"Page summary ({char_count} chars total)",
                extraction_method="llm",
                sub_question_id=sq_id,
            ))

    print(f"  Collected {len(sources)} sources, {len(evidence)} evidence items, {len(gaps)} gaps")

    bundle = EvidenceBundle(
        question=research_q,
        sources=sources,
        evidence=evidence,
        gaps=gaps,
        imported_from="brave_search",
    )

    # Score source quality (LLM-based, batch)
    from grounded_research.source_quality import score_source_quality
    print("  Scoring source quality...")
    await score_source_quality(bundle, trace_id, max_budget=max_budget * 0.05)
    tier_counts = {}
    for s in bundle.sources:
        tier_counts[s.quality_tier] = tier_counts.get(s.quality_tier, 0) + 1
    print(f"  Source quality: {tier_counts}")

    return bundle


def _select_diverse(results: list[dict], max_items: int) -> list[dict]:
    """Select results with diversity across search queries.

    Round-robin picks from each query's results to avoid one query
    dominating the evidence set.
    """
    by_query: dict[str, list[dict]] = {}
    for r in results:
        q = r.get("search_query", "")
        by_query.setdefault(q, []).append(r)

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


