"""Shared evidence utilities used by collection and verification.

Avoids duplication of freshness mapping and recency estimation logic.
Includes staleness detection per Tyler feedback.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

# Freshness filter for the shared search-provider tool
FRESHNESS_MAP = {
    "time_sensitive": "pd",  # past day for fast-moving topics
    "mixed": "py",           # past year for general topics
    "stable": "none",        # no freshness filter for timeless topics
}

# For evidence collection (broader), use past month for time-sensitive
COLLECTION_FRESHNESS_MAP = {
    "time_sensitive": "pm",  # past month (broader than verification)
    "mixed": "py",
    "stable": "none",
}


def estimate_recency(age: str) -> float:
    """Estimate a recency score (0.0-1.0) from Brave's age string.

    Examples: '2 days ago', '3 months ago', '1 year ago'.
    Returns 0.5 for unknown/empty strings.
    """
    if not age:
        return 0.5

    age_lower = age.lower()
    if "hour" in age_lower or "minute" in age_lower:
        return 0.95
    if "day" in age_lower:
        return 0.90
    if "week" in age_lower:
        return 0.80
    if "month" in age_lower:
        parts = age_lower.split()
        try:
            months = int(parts[0])
            return max(0.4, 0.80 - months * 0.05)
        except (ValueError, IndexError):
            return 0.65
    if "year" in age_lower:
        parts = age_lower.split()
        try:
            years = int(parts[0])
            return max(0.1, 0.3 - (years - 1) * 0.1)
        except (ValueError, IndexError):
            return 0.3
    return 0.5


# ---------------------------------------------------------------------------
# Staleness detection
# ---------------------------------------------------------------------------

_DEPRECATION_PATTERNS = re.compile(
    r"\b(deprecated|end[- ]of[- ]life|no longer supported|no longer maintained|"
    r"sunset|sunsetted|archived|unmaintained|obsolete|discontinued|"
    r"end[- ]of[- ]support|legacy[- ]only)\b",
    re.IGNORECASE,
)

_VERSION_IN_URL_PATTERN = re.compile(
    r"[/.]v?\d+\.\d+[/.]",
)

_YEAR_MENTION_PATTERN = re.compile(
    r"\b(19\d{2}|20\d{2})\b",
)


def detect_staleness(
    content: str,
    url: str = "",
    current_year: int | None = None,
    max_age_years: int = 2,
) -> list[str]:
    """Detect staleness signals in fetched page content.

    Returns a list of warning strings (empty if no staleness detected).
    Three checks per Tyler feedback:
    1. Deprecation keywords in content
    2. Version number in URL (may indicate outdated version-specific docs)
    3. Year mentions — flag if latest year in content is >max_age_years old
    """
    if current_year is None:
        current_year = datetime.now(timezone.utc).year

    warnings: list[str] = []

    # Check 1: Deprecation keywords
    match = _DEPRECATION_PATTERNS.search(content[:5000])
    if match:
        warnings.append(f"staleness:deprecation_keyword:{match.group()}")

    # Check 2: Version in URL
    if url and _VERSION_IN_URL_PATTERN.search(url):
        warnings.append(f"staleness:version_in_url:{url[:100]}")

    # Check 3: Year mentions — find the most recent year mentioned
    year_matches = _YEAR_MENTION_PATTERN.findall(content[:10000])
    if year_matches:
        latest_year = max(int(y) for y in year_matches)
        if current_year - latest_year > max_age_years:
            warnings.append(
                f"staleness:outdated_years:latest_mention={latest_year},current={current_year}"
            )

    return warnings
