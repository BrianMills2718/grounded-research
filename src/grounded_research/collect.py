"""Evidence collection from a research question.

Takes a question string and automatically builds an EvidenceBundle by:
1. Generating search queries via LLM
2. Searching via Brave Search API
3. Fetching and extracting content from top results
4. Structuring everything into an EvidenceBundle

This bridges the gap between "user asks a question" and "pipeline has
an evidence bundle to analyze." It uses research_v3's proven search
and fetch tools.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from grounded_research.config import get_model, load_config
from grounded_research.models import (
    EvidenceBundle,
    EvidenceItem,
    ResearchQuestion,
    SourceRecord,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


async def generate_search_queries(
    question: str,
    trace_id: str,
    max_budget: float = 0.5,
    num_queries: int = 5,
) -> list[str]:
    """Generate diverse search queries for a research question via LLM."""
    from llm_client import acall_llm_structured
    from pydantic import BaseModel, Field

    class SearchQueries(BaseModel):
        """LLM output: search queries for evidence collection."""
        queries: list[str] = Field(description="Diverse search queries to gather evidence.")

    model = get_model("analyst")
    result, _meta = await acall_llm_structured(
        model,
        [
            {"role": "system", "content": (
                "Generate diverse search queries to gather evidence for answering "
                "a research question. Include queries that would find: "
                "(1) arguments FOR the main thesis, "
                "(2) arguments AGAINST or alternatives, "
                "(3) concrete data/benchmarks, "
                "(4) real-world experience reports, "
                "(5) expert opinions or reviews. "
                f"Generate exactly {num_queries} queries."
            )},
            {"role": "user", "content": question},
        ],
        response_model=SearchQueries,
        task="query_generation",
        trace_id=f"{trace_id}/queries",
        max_budget=max_budget,
    )
    return result.queries


async def collect_evidence(
    question: str,
    trace_id: str,
    max_sources: int = 10,
    max_budget: float = 1.0,
    time_sensitivity: str = "mixed",
    scope_notes: str = "",
) -> EvidenceBundle:
    """Collect evidence for a research question from web sources.

    Searches the web, fetches top results, and structures everything
    into an EvidenceBundle ready for the adjudication pipeline.
    """
    from grounded_research.tools.brave_search import search_web
    from grounded_research.tools.fetch_page import fetch_page, set_pages_dir

    # Set up pages directory for full-text caching
    pages_dir = _PROJECT_ROOT / "output" / "pages"
    set_pages_dir(pages_dir)

    research_q = ResearchQuestion(
        text=question,
        time_sensitivity=time_sensitivity,
        scope_notes=scope_notes,
    )

    print(f"  Generating search queries...")
    queries = await generate_search_queries(question, trace_id, max_budget=max_budget * 0.1)
    print(f"  Generated {len(queries)} queries")

    # Search across all queries, deduplicate by URL
    all_search_results: list[dict] = []
    seen_urls: set[str] = set()

    for q in queries:
        try:
            raw = await search_web(q, count=5)
            data = json.loads(raw)
            for r in data.get("results", []):
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    r["search_query"] = q
                    all_search_results.append(r)
        except Exception as e:
            print(f"  Search failed for '{q[:40]}...': {e}")

    print(f"  Found {len(all_search_results)} unique URLs across {len(queries)} queries")

    # Take top results by diversity (pick from different queries)
    selected = all_search_results[:max_sources]

    # Fetch page content for each result
    sources: list[SourceRecord] = []
    evidence: list[EvidenceItem] = []
    gaps: list[str] = []

    for i, result in enumerate(selected):
        url = result["url"]
        title = result.get("title", "")
        description = result.get("description", "")

        source = SourceRecord(
            url=url,
            title=title,
            source_type="web_search",
            quality_tier="reliable",
            retrieved_at=datetime.now(timezone.utc),
            recency_score=0.7,
        )
        sources.append(source)

        # Add search snippet as initial evidence
        if description:
            evidence.append(EvidenceItem(
                source_id=source.id,
                content=description,
                content_type="summary",
                relevance_note=f"Search snippet for: {result.get('search_query', '')}",
                extraction_method="upstream",
            ))

        # Fetch full page content
        try:
            print(f"  Fetching [{i+1}/{len(selected)}] {url[:60]}...")
            raw_page = await fetch_page(url, question=question)
            page_data = json.loads(raw_page)

            if page_data.get("error"):
                gaps.append(f"Failed to fetch {url}: {page_data['error']}")
                continue

            # Add key section as evidence if available
            key_section = page_data.get("key_section", "")
            if key_section and len(key_section) > 50:
                evidence.append(EvidenceItem(
                    source_id=source.id,
                    content=key_section,
                    content_type="text",
                    relevance_note=f"Key section extracted for: {question[:60]}",
                    extraction_method="llm",
                ))

            # Add notes as evidence if key_section wasn't useful
            notes = page_data.get("notes", "")
            if notes and not key_section and len(notes) > 50:
                evidence.append(EvidenceItem(
                    source_id=source.id,
                    content=notes,
                    content_type="summary",
                    relevance_note="Page summary (key section extraction failed)",
                    extraction_method="llm",
                ))

        except Exception as e:
            gaps.append(f"Failed to fetch {url}: {e}")

    print(f"  Collected {len(sources)} sources, {len(evidence)} evidence items")

    return EvidenceBundle(
        question=research_q,
        sources=sources,
        evidence=evidence,
        gaps=gaps,
        imported_from="brave_search",
    )
