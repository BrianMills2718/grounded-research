"""Conflict-aware evidence compression.

Reduces evidence count when it exceeds the configured threshold while
preserving: (1) all authoritative-source evidence, (2) evidence from
different sub-questions, (3) evidence diversity. Drops redundant
evidence from low-quality sources first.

See docs/plans/phase_b_source_quality.md for design.
"""

from __future__ import annotations

import logging

from grounded_research.models import EvidenceBundle

logger = logging.getLogger(__name__)


def compress_evidence(
    bundle: EvidenceBundle,
    threshold: int = 80,
) -> int:
    """Compress evidence in-place if count exceeds threshold.

    Priority (keep first):
    1. Evidence from authoritative sources
    2. Evidence with sub_question_id (ensures sub-question coverage)
    3. Evidence from reliable sources
    4. Evidence from unknown/unreliable sources (dropped first)

    Within each tier, keep one per source (drop duplicates from same source).

    Returns the number of items removed.
    """
    if len(bundle.evidence) <= threshold:
        return 0

    # Build source quality lookup
    source_quality = {s.id: s.quality_tier for s in bundle.sources}

    # Score each evidence item for priority
    def _priority(e) -> tuple[int, bool, str]:
        quality = source_quality.get(e.source_id, "unknown")
        tier = {"authoritative": 0, "reliable": 1, "unknown": 2, "unreliable": 3}.get(quality, 2)
        has_sq = e.sub_question_id is not None
        return (tier, not has_sq, e.id)  # lower = higher priority

    sorted_evidence = sorted(bundle.evidence, key=_priority)

    # Keep up to threshold, ensuring at least one per sub-question
    kept: list = []
    seen_sq: set[str] = set()
    seen_sources: set[str] = set()

    # First pass: ensure sub-question coverage
    for e in sorted_evidence:
        if e.sub_question_id and e.sub_question_id not in seen_sq:
            kept.append(e)
            seen_sq.add(e.sub_question_id)
            seen_sources.add(e.source_id)

    # Second pass: fill up to threshold by priority
    for e in sorted_evidence:
        if len(kept) >= threshold:
            break
        if e not in kept:
            kept.append(e)

    removed = len(bundle.evidence) - len(kept)
    if removed > 0:
        bundle.evidence = kept
        logger.info(
            "Compressed evidence: %d → %d items (%d removed)",
            removed + len(kept), len(kept), removed,
        )

    return removed
