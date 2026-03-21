# ADR 0003: Jina Reader Fallback for Blocked Pages

## Status

Accepted

## Date

2026-03-21

## Context

The evidence collection phase fetches page content from URLs found via Brave
Search. Many high-value sources (Medium, Substack, ResearchGate, some blogs)
return HTTP 403 when fetched with a standard HTTP client because they block
automated scraping.

In the Obsidian second brain test run, 10 of 20 fetched URLs returned 403 —
50% evidence loss from fetchable sources. These are often the most detailed
and opinionated sources (long-form blog posts, research papers, experience
reports).

`sam_gov/core/jina_reader.py` already solves this problem by routing requests
through the Jina Reader API (`https://r.jina.ai/`), which renders pages via
a headless browser and returns clean markdown. This works for paywalled and
scraping-blocked sites that allow browser access.

## Decision

Add Jina Reader as a fallback fetcher in the evidence collection phase.

The fetch strategy for each URL:

1. Try direct fetch via `fetch_page()` (research_v3 tool — fast, no API dependency)
2. If direct fetch returns HTTP 403 or empty content, retry via Jina Reader
3. Jina Reader returns markdown content that becomes the evidence item

No API key is required for Jina Reader at 20 requests/minute. With a key
(JINA_API_KEY), the rate limit increases to 200 requests/minute.

## Consequences

### Positive

- Recovers evidence from 403-blocked sources (Medium, Substack, ResearchGate)
- Uses proven code from `sam_gov/core/jina_reader.py`
- Jina Reader returns clean markdown (better for LLM consumption than raw HTML)
- No API key required for basic use
- Fallback-only — does not slow down sources that work with direct fetch

### Negative

- Adds an external API dependency (Jina AI)
- Jina Reader is slower than direct fetch (~3-5 seconds per page)
- Some sites may block Jina Reader too (rare)
- Rate limit of 20/min without key may be constraining for large runs

## Follow-On Rules

1. Direct fetch is always tried first. Jina is fallback only.
2. If JINA_API_KEY is set, use it for higher rate limits.
3. Log which fetch method succeeded for each URL in the trace.
4. If Jina also fails, record the gap — do not silently drop the source.
