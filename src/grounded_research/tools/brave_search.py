"""Brave Search API tool — web search with recency support.

Requires BRAVE_SEARCH_API_KEY.
Adapted from research_v3/tools/brave_search.py with freshness filtering.
"""

import json
import os
from typing import Literal

import httpx

TIMEOUT = 15

Freshness = Literal["pd", "pw", "pm", "py", "none"]


async def search_web(
    query: str,
    count: int = 10,
    freshness: Freshness = "none",
) -> str:
    """Search the web using Brave Search API.

    Returns JSON with results array (title, url, description, age).

    Args:
        query: Search query string.
        count: Number of results (max 20).
        freshness: Recency filter. "pd" = past day, "pw" = past week,
                   "pm" = past month, "py" = past year, "none" = no filter.

    Limits: Max 20 results per query. Rate: 2,000 queries/month free tier.
    """
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not api_key:
        raise RuntimeError("BRAVE_SEARCH_API_KEY not set.")

    params: dict[str, str | int] = {
        "q": query,
        "count": min(count, 20),
    }
    if freshness != "none":
        params["freshness"] = freshness

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params=params,
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": api_key,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    web_results = data.get("web", {}).get("results", [])
    result = {
        "source": "Brave Search",
        "query": query,
        "freshness": freshness,
        "results": [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "description": r.get("description", ""),
                "age": r.get("age", ""),
            }
            for r in web_results
        ],
    }
    return json.dumps(result, default=str)
