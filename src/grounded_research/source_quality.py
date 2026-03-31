"""Deterministic source quality scoring via URL domain lookup.

Tyler V1 spec (Build Plan §Stage 2): "URL lookup table (1.0 official docs →
0.3 generic blog). Unknown sources default to 0.5 (not penalized)."

This is intentionally NOT LLM-based. Quality scoring is a mechanical task
that Tyler specified as a lookup table for determinism and speed.
"""

from __future__ import annotations

import logging
from typing import Literal
from urllib.parse import urlparse

from grounded_research.models import EvidenceBundle

logger = logging.getLogger(__name__)

QualityTier = Literal["authoritative", "reliable", "unknown", "unreliable"]

# --- Domain pattern tables ---
# Tyler spec: 1.0 official docs, 0.8 academic, 0.7 practitioner/news,
# 0.5 unknown, 0.3 generic blog. We map to quality_tier categories.

# authoritative: government, IGOs, peer-reviewed, established think tanks
_AUTHORITATIVE_DOMAINS: set[str] = {
    # Government
    "gov", "mil", "europa.eu", "un.org", "who.int", "worldbank.org",
    "imf.org", "oecd.org", "wto.org", "iaea.org",
    # US government
    "epa.gov", "fda.gov", "cdc.gov", "nih.gov", "bls.gov", "census.gov",
    "state.gov", "treasury.gov", "gao.gov", "cbo.gov", "usaid.gov",
    "federalregister.gov", "congress.gov", "supremecourt.gov",
    # Academic publishers & indices
    "ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov", "nature.com",
    "science.org", "thelancet.com", "nejm.org", "bmj.com", "cell.com",
    "pnas.org", "apa.org", "ieee.org", "acm.org", "jstor.org",
    "wiley.com", "springer.com", "sciencedirect.com", "tandfonline.com",
    "oxfordjournals.org", "cambridge.org",
    # Think tanks
    "brookings.edu", "rand.org", "cfr.org", "csis.org", "piie.com",
    "bruegel.org", "chathamhouse.org", "iiss.org", "carnegieendowment.org",
    "nber.org",
}

_AUTHORITATIVE_TLD_SUFFIXES: set[str] = {".gov", ".mil"}
_ACADEMIC_TLD_SUFFIXES: set[str] = {".edu", ".ac.uk", ".edu.au"}

# reliable: major news, professional orgs, established industry
_RELIABLE_DOMAINS: set[str] = {
    # News
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "nytimes.com",
    "washingtonpost.com", "theguardian.com", "ft.com", "economist.com",
    "wsj.com", "bloomberg.com", "politico.com", "axios.com",
    "npr.org", "pbs.org", "aljazeera.com",
    # Tech / industry
    "arxiv.org", "github.com", "stackoverflow.com", "techcrunch.com",
    "wired.com", "arstechnica.com", "theverge.com",
    # Research orgs (not quite think-tank tier)
    "pewresearch.org", "gallup.com", "statista.com",
    "poverty-action.org", "givedirectly.org",
    # Preprint / open access
    "ssrn.com", "researchgate.net", "semanticscholar.org",
    "biorxiv.org", "medrxiv.org",
}

# unreliable: known misinformation, SEO farms, content mills
_UNRELIABLE_DOMAINS: set[str] = {
    "coursehero.com", "chegg.com", "brainly.com",
    "trendingworld.info", "contentfarm.example",
}

# deprioritized (mapped to "unknown" — not penalized but not trusted)
_UNKNOWN_DOMAINS: set[str] = {
    "wikipedia.org", "medium.com", "substack.com",
    "blogspot.com", "wordpress.com",
    "youtube.com", "reddit.com", "twitter.com", "x.com",
    "facebook.com", "linkedin.com", "quora.com",
    "tiktok.com", "instagram.com",
}


def _extract_domain(url: str) -> str:
    """Extract the effective domain from a URL for matching."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        # Strip www. prefix
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def _classify_domain(domain: str) -> QualityTier:
    """Classify a domain into a quality tier using pattern matching.

    Tyler spec: unknown defaults to 0.5 (not penalized).
    """
    if not domain:
        return "unknown"

    # Check TLD suffixes first (catches all .gov, .edu, .mil domains)
    for suffix in _AUTHORITATIVE_TLD_SUFFIXES:
        if domain.endswith(suffix):
            return "authoritative"
    for suffix in _ACADEMIC_TLD_SUFFIXES:
        if domain.endswith(suffix):
            return "authoritative"

    # Check exact domain or parent domain matches
    # For "sub.example.com", check "sub.example.com", "example.com"
    parts = domain.split(".")
    for i in range(len(parts)):
        candidate = ".".join(parts[i:])
        if candidate in _AUTHORITATIVE_DOMAINS:
            return "authoritative"
        if candidate in _RELIABLE_DOMAINS:
            return "reliable"
        if candidate in _UNRELIABLE_DOMAINS:
            return "unreliable"
        if candidate in _UNKNOWN_DOMAINS:
            return "unknown"

    # PDF URLs get a small boost — Tyler spec mentions PDF bonus in ranking
    # but for quality tier, we keep it as unknown unless domain matches
    return "unknown"


async def score_source_quality(
    bundle: EvidenceBundle,
    trace_id: str,
    max_budget: float = 0.5,
) -> None:
    """Score source quality for all sources in the bundle (in place).

    Deterministic URL-based lookup per Tyler V1 spec. No LLM call.
    The trace_id and max_budget params are kept for API compatibility
    but are not used (no LLM call to track).
    """
    if not bundle.sources:
        return

    updated = 0
    for source in bundle.sources:
        domain = _extract_domain(source.url)
        tier = _classify_domain(domain)
        source.quality_tier = tier
        updated += 1

    tier_counts: dict[str, int] = {}
    for s in bundle.sources:
        tier_counts[s.quality_tier] = tier_counts.get(s.quality_tier, 0) + 1

    logger.info(
        "Scored %d sources (deterministic lookup): %s",
        updated,
        ", ".join(f"{k}={v}" for k, v in sorted(tier_counts.items())),
    )
