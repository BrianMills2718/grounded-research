"""Evidence ingest adapters.

Normalizes upstream evidence bundles (manual JSON, research_v3 graph.yaml)
into the internal EvidenceBundle schema. Validates referential integrity
and preserves provenance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from grounded_research.models import (
    EvidenceBundle,
    EvidenceItem,
    ResearchQuestion,
    SourceRecord,
)


def load_manual_bundle(path: Path) -> EvidenceBundle:
    """Load a manually curated JSON evidence bundle.

    Expected format matches tests/fixtures/session_storage_bundle.json:
    {
      "question": {...},
      "sources": [...],
      "evidence": [...],
      "gaps": [...],
      "imported_from": "manual"
    }
    """
    raw = json.loads(path.read_text())
    return _build_bundle(raw, imported_from=raw.get("imported_from", "manual"))


def load_research_v3_bundle(graph_path: Path, query: str) -> EvidenceBundle:
    """Load a research_v3 graph.yaml into an EvidenceBundle.

    Maps research_v3 models:
    - InvestigationGoal.original_query → ResearchQuestion.text
    - Source → SourceRecord (credibility → quality_tier)
    - Claim.statement → EvidenceItem.content (each claim = one evidence item)
    """
    raw = yaml.safe_load(graph_path.read_text())

    question = ResearchQuestion(
        text=query or raw.get("goal", {}).get("original_query", ""),
        time_sensitivity="mixed",
    )

    # Map sources
    source_map: dict[str, SourceRecord] = {}
    for sid, src in (raw.get("sources") or {}).items():
        source_map[sid] = SourceRecord(
            url=src.get("url", ""),
            title=src.get("url", "")[:80],
            source_type=src.get("source_type", "other"),
            quality_tier=src.get("credibility", "unknown"),
            api_record_id=src.get("api_record_id"),
            upstream_source_id=sid,
        )

    # Map claims → evidence items
    evidence: list[EvidenceItem] = []
    for claim in raw.get("claims") or []:
        src = claim.get("source", {})
        src_id = src.get("id", "")
        # Find or create source record
        if src_id not in source_map and src.get("url"):
            source_map[src_id] = SourceRecord(
                url=src["url"],
                source_type=src.get("source_type", "other"),
                quality_tier=src.get("credibility", "unknown"),
                upstream_source_id=src_id,
            )
        if src_id in source_map:
            evidence.append(
                EvidenceItem(
                    source_id=source_map[src_id].id,
                    content=claim.get("statement", ""),
                    content_type="text",
                    extraction_method="upstream",
                )
            )

    # Extract gaps from open knowledge gaps
    gaps = [g.get("description", "") for g in (raw.get("gaps") or []) if g.get("status") == "open"]

    return EvidenceBundle(
        question=question,
        sources=list(source_map.values()),
        evidence=evidence,
        gaps=gaps,
        imported_from="research_v3",
    )


def _build_bundle(raw: dict[str, Any], imported_from: str) -> EvidenceBundle:
    """Build an EvidenceBundle from a raw dict, validating referential integrity."""
    question = ResearchQuestion(**raw["question"])
    sources = [SourceRecord(**s) for s in raw.get("sources", [])]
    evidence = [EvidenceItem(**e) for e in raw.get("evidence", [])]

    bundle = EvidenceBundle(
        question=question,
        sources=sources,
        evidence=evidence,
        gaps=raw.get("gaps", []),
        imported_from=imported_from,
    )

    # Validate referential integrity
    source_ids = {s.id for s in bundle.sources}
    orphans = [e.id for e in bundle.evidence if e.source_id not in source_ids]
    if orphans:
        raise ValueError(f"Evidence items reference unknown sources: {orphans}")

    return bundle


def validate_bundle(bundle: EvidenceBundle) -> list[str]:
    """Validate an EvidenceBundle and return a list of warnings (empty = clean)."""
    warnings: list[str] = []
    source_ids = {s.id for s in bundle.sources}

    for e in bundle.evidence:
        if e.source_id not in source_ids:
            warnings.append(f"Evidence {e.id} references unknown source {e.source_id}")

    if not bundle.evidence:
        warnings.append("Evidence bundle is empty")

    if not bundle.question.text:
        warnings.append("Research question text is empty")

    sources_without_evidence = source_ids - {e.source_id for e in bundle.evidence}
    if sources_without_evidence:
        warnings.append(f"Sources with no evidence items: {sources_without_evidence}")

    return warnings
