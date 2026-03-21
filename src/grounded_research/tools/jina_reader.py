"""Jina Reader — fallback page fetcher for 403-blocked sites.

Routes requests through Jina AI's Reader API which renders pages via
headless browser and returns clean markdown. Works for Medium, Substack,
ResearchGate, and other sites that block direct HTTP scraping.

Adapted from sam_gov/core/jina_reader.py.

Rate limits:
- Without JINA_API_KEY: 20 requests/minute
- With JINA_API_KEY: 200 requests/minute

API: https://jina.ai/reader/
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import httpx

JINA_READER_BASE = "https://r.jina.ai/"
TIMEOUT = 30


async def fetch_page_jina(url: str, question: str = "") -> str:
    """Fetch a URL via Jina Reader and return structured JSON result.

    Returns the same JSON shape as fetch_page.py for compatibility:
    {url, content_type, char_count, notes, key_section, question, note}

    Falls back gracefully on error — returns JSON with error field.
    """
    jina_url = f"{JINA_READER_BASE}{url}"
    api_key = os.environ.get("JINA_API_KEY")

    headers = {"Accept": "text/markdown"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(jina_url, headers=headers)

            if resp.status_code != 200:
                return json.dumps({
                    "url": url,
                    "fetched_via": "jina_reader",
                    "error": f"Jina Reader HTTP {resp.status_code}",
                })

            content = resp.text

            # Extract title from first markdown heading
            title = ""
            for line in content.split("\n")[:10]:
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            # Truncate for evidence extraction
            notes = content[:500]
            key_section = _extract_key_section(content, question) if question else ""

            return json.dumps({
                "url": url,
                "fetched_via": "jina_reader",
                "content_type": "text/markdown",
                "title": title,
                "char_count": len(content),
                "notes": notes,
                "key_section": key_section,
                "question": question,
                "note": "Fetched via Jina Reader (fallback for 403-blocked sites).",
            })

    except httpx.TimeoutException:
        return json.dumps({
            "url": url,
            "fetched_via": "jina_reader",
            "error": "Jina Reader request timed out",
        })
    except Exception as e:
        return json.dumps({
            "url": url,
            "fetched_via": "jina_reader",
            "error": f"Jina Reader failed: {type(e).__name__}: {e}",
        })


def _extract_key_section(text: str, question: str, max_chars: int = 1500) -> str:
    """Extract the most relevant section of markdown for a given question.

    Scores paragraphs by keyword overlap, returns highest-scoring in order.
    """
    if not question or not text:
        return text[:max_chars]

    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to",
        "for", "of", "and", "or", "but", "what", "when", "where", "who", "how",
        "why", "did", "does", "do", "has", "have", "had", "be", "been", "being",
        "this", "that", "which", "it", "its", "with", "from", "by", "as",
        "best", "can", "you", "your",
    }
    keywords = {
        w.lower().strip(".,?!\"'")
        for w in question.split()
        if w.lower().strip(".,?!\"'") not in stopwords and len(w) > 2
    }

    if not keywords:
        return text[:max_chars]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.strip()) > 20]

    def score(para: str) -> int:
        pl = para.lower()
        return sum(1 for k in keywords if k in pl)

    scored = sorted(range(len(paragraphs)), key=lambda i: score(paragraphs[i]), reverse=True)

    selected: list[int] = []
    total = 0
    for i in scored:
        if score(paragraphs[i]) == 0:
            break
        if total + len(paragraphs[i]) > max_chars:
            continue
        selected.append(i)
        total += len(paragraphs[i]) + 2
        if total >= max_chars:
            break

    if not selected:
        return text[:max_chars]

    return "\n\n".join(paragraphs[i] for i in sorted(selected))
