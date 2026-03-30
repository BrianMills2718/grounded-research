"""Shared evidence utilities used by collection and verification.

Avoids duplication of freshness mapping and recency estimation logic.
"""

from __future__ import annotations

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
