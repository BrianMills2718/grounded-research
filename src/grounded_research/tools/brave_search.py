"""Brave Search API tool powered by the shared open-web retrieval substrate."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Literal

from llm_client.observability import log_tool_call
from open_web_retrieval import OpenWebRetrievalClient, SearchQuery

Freshness = Literal["pd", "pw", "pm", "py", "none"]
from open_web_retrieval.exceptions import OpenWebRetrievalError


def _freshness_days(freshness: Freshness) -> int | None:
    """Convert Brave freshness filters into Brave-compatible day windows."""
    mapping = {
        "pd": 1,
        "pw": 7,
        "pm": 30,
        "py": 365,
        "none": None,
    }
    return mapping[freshness]


async def search_web(
    query: str,
    count: int = 10,
    freshness: Freshness = "none",
    *,
    trace_id: str | None = None,
    task: str = "collection.search",
) -> str:
    """Search the web using the shared Brave adapter and return normalized results.

    The return schema remains compatible with historical callers (`results` entries
    include `title`, `url`, `description`, and `age`) so that downstream
    `collect.py` logic is unaffected.
    """
    if not query.strip():
        raise ValueError("query is required")

    api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not api_key:
        raise RuntimeError("BRAVE_SEARCH_API_KEY not set.")

    effective_count = max(1, min(count, 20))
    query_model = SearchQuery(
        query=query,
        providers=("brave",),
        top_k=effective_count,
        recency_days=_freshness_days(freshness),
        locale="en",
    )
    client = OpenWebRetrievalClient(brave_api_key=api_key, tool_call_logger=log_tool_call)
    try:
        hits = client.search(query_model, trace_id=trace_id, task=task)
    except OpenWebRetrievalError as exc:
        if (
            getattr(exc, "error_code", "") == "OPEN_WEB_RETRIEVAL_ERROR"
            and "search returned no results" in str(exc)
        ):
            return json.dumps(
                {
                    "source": "Brave Search",
                    "query": query,
                    "freshness": freshness,
                    "results": [],
                },
                default=str,
            )
        raise

    results: list[dict[str, str]] = []
    for hit in hits[:effective_count]:
        payload = hit.raw_payload if isinstance(hit.raw_payload, Mapping) else {}
        results.append(
            {
                "title": hit.title or "",
                "url": hit.url,
                "description": hit.snippet or "",
                "age": str(payload.get("age", "")),
            },
        )

    return json.dumps(
        {
            "source": "Brave Search",
            "query": query,
            "freshness": freshness,
            "results": results,
        },
        default=str,
    )
