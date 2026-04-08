"""Deterministic source quality scoring via URL domain lookup.

Tyler V1 spec (Build Plan §Stage 2): "URL lookup table (1.0 official docs →
0.3 generic blog). Unknown sources default to 0.5 (not penalized)."

This is intentionally NOT LLM-based. Quality scoring is a mechanical task
that Tyler specified as a lookup table for determinism and speed.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from typing import Literal
from urllib.parse import urlparse

from grounded_research.config import get_source_quality_config
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

_BLOG_DOMAINS: set[str] = {
    "medium.com", "substack.com", "blogspot.com", "wordpress.com",
}

_FORUM_DOMAINS: set[str] = {
    "reddit.com", "news.ycombinator.com", "twitter.com", "x.com",
    "facebook.com", "linkedin.com", "quora.com", "tiktok.com", "instagram.com",
}

_AUTHORITY_FLOOR_PATTERNS: tuple[str, ...] = (
    "rfc",
    "w3.org",
    "/spec",
    "/specification",
    "/standard",
    "/api/",
    "/docs/",
    "/documentation/",
)

_DEPRECATION_PATTERN = re.compile(
    r"\b(?:deprecated|end-of-life|no longer maintained|use .+ instead|this page has moved)\b",
    re.IGNORECASE,
)
_VERSION_IN_URL_PATTERN = re.compile(r"/v(\d+)/", re.IGNORECASE)
_YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")


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


def _authority_score_for_source_url(*, url: str, source_type: str) -> float:
    """Resolve Tyler's deterministic authority score from URL and source type."""
    domain = _extract_domain(url)
    url_lower = url.lower()
    if source_type in {"government_db", "primary_document", "platform_transparency"}:
        return 1.0
    if any(pattern in url_lower for pattern in ("/docs/", "/documentation/", "/api/")):
        return 1.0
    if source_type == "academic":
        return 0.9
    if domain.endswith(".edu") or domain.endswith(".ac.uk") or domain.endswith(".edu.au"):
        return 0.9
    if "github.com" in domain:
        return 0.8
    if domain in _BLOG_DOMAINS:
        return 0.3
    if domain in _FORUM_DOMAINS or source_type == "social_media":
        return 0.5
    tier = _classify_domain(domain)
    if tier == "authoritative":
        return 1.0
    if tier == "reliable":
        return 0.7
    if tier == "unreliable":
        return 0.3
    return 0.5


def _resolve_topic_policy(cfg: dict[str, object]) -> tuple[int, float]:
    """Resolve the current Stage 2 topic half-life and temporal weight."""
    topic = str(cfg.get("default_topic", "default"))
    half_life_days = int(dict(cfg.get("half_life_days", {})).get(topic, dict(cfg.get("half_life_days", {})).get("default", 1095)))
    temporal_weight = float(dict(cfg.get("temporal_weight", {})).get(topic, dict(cfg.get("temporal_weight", {})).get("default", 0.2)))
    return half_life_days, temporal_weight


def _blend_authority_and_freshness(
    *,
    authority_score: float,
    published_at,
    cfg: dict[str, object],
) -> float:
    """Blend authority with freshness using Tyler's Stage 2 scoring rule."""
    if published_at is None:
        return authority_score

    half_life_days, temporal_weight = _resolve_topic_policy(cfg)
    now = datetime.now(tz=published_at.tzinfo or timezone.utc)
    age_days = max(0.0, (now - published_at).total_seconds() / 86400.0)
    freshness = 0.5 ** (age_days / max(1.0, float(half_life_days)))
    return (temporal_weight * freshness) + ((1.0 - temporal_weight) * authority_score)


def _apply_authority_floor(score: float, *, url: str, title: str, cfg: dict[str, object]) -> float:
    """Apply Tyler's authority floor for seminal or official specifications."""
    authority_floor = float(cfg.get("authority_floor", 0.4))
    haystack = f"{url.lower()} {title.lower()}"
    if any(pattern in haystack for pattern in _AUTHORITY_FLOOR_PATTERNS):
        return max(score, authority_floor)
    return score


def _apply_staleness_modifiers(
    score: float,
    *,
    url: str,
    content_excerpt: str,
    cfg: dict[str, object],
) -> float:
    """Apply Tyler's deterministic staleness penalties."""
    adjusted = score
    excerpt = (content_excerpt or "")[:2000]

    if _DEPRECATION_PATTERN.search(excerpt):
        adjusted = max(0.1, adjusted - float(cfg.get("deprecation_penalty", 0.3)))

    current_versions = dict(cfg.get("current_versions", {}))
    version_match = _VERSION_IN_URL_PATTERN.search(url)
    if version_match:
        version_num = int(version_match.group(1))
        url_lower = url.lower()
        for api_name, current_version in current_versions.items():
            if str(api_name).lower() in url_lower and version_num < int(current_version):
                adjusted = max(0.1, adjusted - float(cfg.get("stale_year_penalty", 0.15)))
                break

    years = [int(year) for year in _YEAR_PATTERN.findall(excerpt)]
    half_life_days, _ = _resolve_topic_policy(cfg)
    if years and half_life_days <= 1095 and max(years) < (datetime.now().year - 2):
        adjusted = max(0.1, adjusted - float(cfg.get("stale_year_penalty", 0.15)))

    return adjusted


async def score_source_quality(
    bundle: EvidenceBundle,
    trace_id: str,
    max_budget: float = 0.5,
    source_text_by_id: dict[str, str] | None = None,
) -> None:
    """Score source quality for all sources in the bundle (in place).

    Deterministic URL-based lookup per Tyler V1 spec. No LLM call.
    The trace_id and max_budget params are kept for API compatibility
    but are not used (no LLM call to track).
    """
    if not bundle.sources:
        return

    del trace_id, max_budget

    cfg = get_source_quality_config()
    updated = 0
    for source in bundle.sources:
        domain = _extract_domain(source.url)
        tier = _classify_domain(domain)
        authority_score = _authority_score_for_source_url(
            url=source.url,
            source_type=source.source_type,
        )
        blended_score = _blend_authority_and_freshness(
            authority_score=authority_score,
            published_at=source.published_at,
            cfg=cfg,
        )
        with_floor = _apply_authority_floor(
            blended_score,
            url=source.url,
            title=source.title,
            cfg=cfg,
        )
        final_score = _apply_staleness_modifiers(
            with_floor,
            url=source.url,
            content_excerpt=(source_text_by_id or {}).get(source.id, ""),
            cfg=cfg,
        )
        source.quality_tier = tier
        source.quality_score = round(final_score, 4)
        source.recency_score = source.quality_score
        updated += 1

    tier_counts: dict[str, int] = {}
    for s in bundle.sources:
        tier_counts[s.quality_tier] = tier_counts.get(s.quality_tier, 0) + 1

    logger.info(
        "Scored %d sources (deterministic authority/freshness/staleness): %s",
        updated,
        ", ".join(f"{k}={v}" for k, v in sorted(tier_counts.items())),
    )
