"""LLM-based source quality scoring.

Batch-scores all sources after fetch, before analyst phase.
Updates SourceRecord.quality_tier from the default "reliable" to
a per-source assessment (authoritative/reliable/unknown/unreliable).

See docs/plans/phase_b_source_quality.md for design decisions.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from grounded_research.config import get_fallback_models, get_model
from grounded_research.models import EvidenceBundle
from grounded_research.runtime_policy import get_request_timeout

logger = logging.getLogger(__name__)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

QualityTier = Literal["authoritative", "reliable", "unknown", "unreliable"]


class _SourceAssessment(BaseModel):
    source_id: str = Field(description="The source ID (S-xxx) being assessed.")
    quality_tier: QualityTier = Field(
        description=(
            "authoritative: government agencies (EPA, WHO, IEA), peer-reviewed journals, "
            "established think tanks (Brookings, CSIS, Bruegel), major IGOs. "
            "reliable: major news outlets (Reuters, BBC, NYT), professional organizations, "
            "well-known industry sources. "
            "unknown: blogs, forums, small sites, unclear provenance. "
            "unreliable: known misinformation, SEO farms, content mills."
        ),
    )


class _SourceQualityBatch(BaseModel):
    assessments: list[_SourceAssessment] = Field(
        description="Quality assessment for each source.",
    )


async def score_source_quality(
    bundle: EvidenceBundle,
    trace_id: str,
    max_budget: float = 0.5,
) -> None:
    """Score source quality for all sources in the bundle (in place).

    Updates SourceRecord.quality_tier from the default to a per-source
    assessment. On failure, logs a warning and leaves all as "reliable".
    """
    from llm_client import acall_llm_structured, render_prompt

    if not bundle.sources:
        return

    # Build compact source descriptions for batch scoring
    source_lines = []
    for s in bundle.sources:
        source_lines.append(f"- {s.id}: {s.title[:80]} | {s.url}")

    try:
        model = get_model("source_scoring")
    except KeyError:
        model = get_model("dispute_classification")  # fallback to same-tier model

    try:
        messages = render_prompt(
            str(_PROJECT_ROOT / "prompts" / "source_scoring.yaml"),
            source_lines=source_lines,
        )
        result, _meta = await acall_llm_structured(
            model,
            messages,
            response_model=_SourceQualityBatch,
            task="source_quality_scoring",
            trace_id=f"{trace_id}/source_quality",
            timeout=get_request_timeout("source_scoring"),
            max_budget=max_budget,
            fallback_models=get_fallback_models("source_scoring") or get_fallback_models("dispute_classification"),
        )

        # Apply scores to sources
        score_map = {a.source_id: a.quality_tier for a in result.assessments}
        updated = 0
        for source in bundle.sources:
            if source.id in score_map:
                source.quality_tier = score_map[source.id]
                updated += 1

        logger.info("Scored %d/%d sources", updated, len(bundle.sources))

    except Exception as e:
        logger.warning("Source quality scoring failed, keeping defaults: %s", e)
