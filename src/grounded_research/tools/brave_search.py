"""Brave Search API tool — web search.

Requires BRAVE_SEARCH_API_KEY.
"""

import json
import os
import httpx

TIMEOUT = 15


async def search_web(query: str, count: int = 10) -> str:
    """Search the web using Brave Search API.

    Returns JSON with results array (title, url, description, age).

    Use this for news, investigations, controversies, and context not
    available in structured government APIs. Good queries include
    "entity name + federal contracts + investigation" or
    "entity name + settlement + enforcement".

    Limits: Max 20 results per query.
    """
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not api_key:
        raise RuntimeError("BRAVE_SEARCH_API_KEY not set.")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": min(count, 20)},
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
