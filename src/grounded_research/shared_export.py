"""Export grounded-research artifacts to shared epistemic-contracts models.

Converts Tyler claim ledger entries, evidence items, and source records
to the shared ecosystem contracts for consumption by onto-canon6 and
other downstream projects.
"""

from __future__ import annotations

from pathlib import Path

from epistemic_contracts import (
    ClaimRecord,
    ConfidenceScore,
    EvidenceItem as SharedEvidenceItem,
    SourceRecord as SharedSourceRecord,
)
from epistemic_contracts.models import EVIDENCE_LABEL_WEIGHTS

from .models import EvidenceItem, SourceRecord
from .tyler_v1_models import ClaimLedgerEntry


def claim_ledger_to_shared(
    entry: ClaimLedgerEntry,
    source_record_ids: list[str] | None = None,
) -> ClaimRecord:
    """Convert a Tyler ClaimLedgerEntry to shared ClaimRecord."""
    # Map evidence label to confidence score
    label = entry.evidence_label.value.lower() if hasattr(entry.evidence_label, 'value') else str(entry.evidence_label).lower()
    weight = EVIDENCE_LABEL_WEIGHTS.get(label, 0.5)

    confidence = ConfidenceScore(
        score=weight,
        source="adjudication",
        evidence_label=label if label in EVIDENCE_LABEL_WEIGHTS else None,  # type: ignore[arg-type]
    )

    # Map status
    status_str = entry.status.value.lower() if hasattr(entry.status, 'value') else str(entry.status).lower()

    return ClaimRecord(
        id=entry.id,
        statement=entry.statement,
        claim_type="fact_claim",
        status=status_str,  # type: ignore[arg-type]
        confidence=confidence,
        source_ids=list(entry.source_references),
        evidence_label=label if label in EVIDENCE_LABEL_WEIGHTS else None,  # type: ignore[arg-type]
        supporting_models=list(entry.supporting_models),
        contesting_models=list(entry.contesting_models),
        is_provisional=entry.is_provisional,
        source_system="grounded-research",
    )


def source_to_shared(record: SourceRecord) -> SharedSourceRecord:
    """Convert a grounded-research SourceRecord to shared SourceRecord."""
    return SharedSourceRecord(
        id=record.id,
        url=record.url,
        title=record.title,
        source_type=record.source_type,  # type: ignore[arg-type]
        quality_tier=record.quality_tier,  # type: ignore[arg-type]
        recency_score=record.recency_score,
        published_at=record.published_at,
        retrieved_at=record.retrieved_at,
        api_record_id=record.api_record_id,
        upstream_source_id=record.upstream_source_id,
    )


def evidence_to_shared(item: EvidenceItem, source_id: str) -> SharedEvidenceItem:
    """Convert a grounded-research EvidenceItem to shared EvidenceItem."""
    return SharedEvidenceItem(
        id=item.id,
        source_id=source_id,
        content=item.content,
        content_type=item.content_type,  # type: ignore[arg-type]
        relevance_note=item.relevance_note,
        extraction_method=item.extraction_method,  # type: ignore[arg-type]
    )


def load_handoff_claims(handoff_path: str | Path) -> list[ClaimRecord]:
    """Load claims from a grounded-research handoff.json into shared ClaimRecords.

    The handoff.json uses a simplified serialization format with
    claim_ledger.claims[] containing {id, statement, status, confidence,
    analyst_sources, evidence_ids, source_raw_claim_ids, status_reason}.
    This function bridges that actual format to shared ClaimRecords.
    """
    import json

    handoff_path = Path(handoff_path)
    data = json.loads(handoff_path.read_text())

    claim_ledger = data.get("claim_ledger", {})
    raw_claims = claim_ledger.get("claims", [])

    # Build source lookup for evidence enrichment
    sources_by_id = {s["id"]: s for s in data.get("sources", [])}
    evidence_by_id = {e["id"]: e for e in data.get("evidence", [])}

    records: list[ClaimRecord] = []
    for raw in raw_claims:
        # Map confidence string to score
        confidence_str = str(raw.get("confidence", "medium")).lower()
        confidence_weights = {"high": 0.8, "medium": 0.5, "low": 0.2}
        score = confidence_weights.get(confidence_str, 0.5)

        confidence = ConfidenceScore(
            score=score,
            source="adjudication",
        )

        # Map status
        status_str = str(raw.get("status", "initial")).lower()

        # Collect source IDs from evidence
        source_ids = []
        for eid in raw.get("evidence_ids", []):
            ev = evidence_by_id.get(eid)
            if ev and ev.get("source_id"):
                source_ids.append(ev["source_id"])
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_source_ids = []
        for sid in source_ids:
            if sid not in seen:
                seen.add(sid)
                unique_source_ids.append(sid)

        record = ClaimRecord(
            id=raw["id"],
            statement=raw["statement"],
            claim_type="fact_claim",
            status=status_str,  # type: ignore[arg-type]
            confidence=confidence,
            source_ids=unique_source_ids,
            supporting_models=raw.get("analyst_sources", []),
            contesting_models=[],
            is_provisional=True,
            source_system="grounded-research",
        )
        records.append(record)

    return records


__all__ = [
    "claim_ledger_to_shared",
    "evidence_to_shared",
    "load_handoff_claims",
    "source_to_shared",
]
