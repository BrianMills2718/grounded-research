"""Shared web search tool backed by configurable `open_web_retrieval` providers."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from collections.abc import Sequence
from typing import Literal

from llm_client.observability import log_tool_call
from open_web_retrieval import OpenWebRetrievalClient, SearchQuery
from open_web_retrieval.exceptions import OpenWebRetrievalError

from grounded_research.config import get_search_provider_config

Freshness = Literal["pd", "pw", "pm", "py", "none"]
SearchDepth = Literal["basic", "advanced"]
ResultDetail = Literal["summary", "chunks"]
SearchCorpus = Literal["general", "news", "academic", "company", "pdf", "github", "people", "personal_site", "financial_report"]


def _freshness_days(freshness: Freshness) -> int | None:
    """Convert project freshness buckets into shared recency-day windows."""
    mapping = {
        "pd": 1,
        "pw": 7,
        "pm": 30,
        "py": 365,
        "none": None,
    }
    return mapping[freshness]


def _provider_source_label(provider: str) -> str:
    """Return the human-readable provider label stored in normalized payloads."""
    labels = {
        "tavily": "Tavily Search",
        "brave": "Brave Search",
        "searxng": "SearxNG Search",
        "exa": "Exa Search",
    }
    return labels[provider]


def _build_client(provider: str) -> OpenWebRetrievalClient:
    """Build the shared retrieval client for the configured provider."""
    kwargs: dict[str, object] = {"tool_call_logger": log_tool_call}
    if provider == "tavily":
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY not set.")
        kwargs["tavily_api_key"] = api_key
    elif provider == "brave":
        api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
        if not api_key:
            raise RuntimeError("BRAVE_SEARCH_API_KEY not set.")
        kwargs["brave_api_key"] = api_key
    elif provider == "exa":
        api_key = os.environ.get("EXA_API_KEY")
        if not api_key:
            raise RuntimeError("EXA_API_KEY not set.")
        kwargs["exa_api_key"] = api_key
    elif provider == "searxng":
        base_url = os.environ.get("SEARXNG_BASE_URL")
        if not base_url:
            raise RuntimeError("SEARXNG_BASE_URL not set.")
        kwargs["searxng_base_url"] = base_url
    else:  # pragma: no cover - config validation should prevent this
        raise ValueError(f"Unsupported search provider: {provider}")
    return OpenWebRetrievalClient(**kwargs)


async def search_web_exa(
    query: str,
    count: int = 5,
    *,
    search_depth: SearchDepth | None = None,
    result_detail: ResultDetail | None = None,
    detail_budget: int | None = None,
    corpus: SearchCorpus | None = None,
    domains_allow: Sequence[str] = (),
    domains_deny: Sequence[str] = (),
    trace_id: str | None = None,
    task: str = "collection.search.exa",
) -> str:
    """Search via Exa (semantic/neural) if EXA_API_KEY is available.

    Tyler V1 §Stage 2: "Tavily (primary) + Exa (secondary, semantic/neural)."
    Returns empty results gracefully if Exa is not configured.
    """
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        return json.dumps({"source": "Exa Search", "query": query, "results": []})

    client = _build_client("exa")
    try:
        query_model = SearchQuery(
            query=query,
            providers=("exa",),
            top_k=max(1, min(count, 10)),
            search_depth=search_depth,
            result_detail=result_detail,
            detail_budget=detail_budget,
            corpus=corpus,
            domains_allow=tuple(domains_allow),
            domains_deny=tuple(domains_deny),
        )
        hits = client.search(query_model, trace_id=trace_id, task=task)
    except Exception:
        return json.dumps({"source": "Exa Search", "query": query, "results": []})
    finally:
        client.close()

    results: list[dict[str, str]] = []
    for hit in hits[:count]:
        payload = hit.raw_payload if isinstance(hit.raw_payload, Mapping) else {}
        results.append({
            "title": hit.title or "",
            "url": hit.url,
            "description": hit.snippet or "",
            "age": str(payload.get("age", "")),
            "score": payload.get("score"),
            "published_at": hit.published_at.isoformat() if hit.published_at else None,
        })

    return json.dumps(
        {"source": "Exa Search", "query": query, "results": results},
        default=str,
    )


async def search_web(
    query: str,
    count: int = 10,
    freshness: Freshness = "none",
    *,
    provider_override: str | None = None,
    search_depth: SearchDepth | None = None,
    result_detail: ResultDetail | None = None,
    detail_budget: int | None = None,
    corpus: SearchCorpus | None = None,
    domains_allow: Sequence[str] = (),
    domains_deny: Sequence[str] = (),
    trace_id: str | None = None,
    task: str = "collection.search",
) -> str:
    """Search the web through the configured shared provider and normalize results.

    The returned JSON shape intentionally stays compatible with current callers:
    `results` entries still include `title`, `url`, `description`, and `age`.
    """
    if not query.strip():
        raise ValueError("query is required")

    provider_cfg = get_search_provider_config()
    provider = provider_override or provider_cfg["provider"]
    locale = provider_cfg["locale"]
    effective_count = max(1, min(count, 20))
    query_model = SearchQuery(
        query=query,
        providers=(provider,),
        top_k=effective_count,
        recency_days=_freshness_days(freshness),
        locale=locale,
        search_depth=search_depth,
        result_detail=result_detail,
        detail_budget=detail_budget,
        corpus=corpus,
        domains_allow=tuple(domains_allow),
        domains_deny=tuple(domains_deny),
    )
    client = _build_client(provider)
    try:
        hits = client.search(query_model, trace_id=trace_id, task=task)
    except OpenWebRetrievalError as exc:
        if (
            getattr(exc, "error_code", "") == "OPEN_WEB_RETRIEVAL_ERROR"
            and "search returned no results" in str(exc)
        ):
            return json.dumps(
                {
                    "source": _provider_source_label(provider),
                    "query": query,
                    "freshness": freshness,
                    "results": [],
                },
                default=str,
            )
        raise
    finally:
        client.close()

    results: list[dict[str, str]] = []
    for hit in hits[:effective_count]:
        payload = hit.raw_payload if isinstance(hit.raw_payload, Mapping) else {}
        published_at = getattr(hit, "published_at", None)
        results.append(
            {
                "title": hit.title or "",
                "url": hit.url,
                "description": hit.snippet or "",
                "age": str(payload.get("age", "")),
                "score": payload.get("score"),
                "published_at": published_at.isoformat() if published_at else None,
            },
        )

    return json.dumps(
        {
            "source": _provider_source_label(provider),
            "query": query,
            "freshness": freshness,
            "results": results,
        },
        default=str,
    )
