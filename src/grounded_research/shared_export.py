"""Export grounded-research artifacts to shared epistemic-contracts models.

Converts Tyler claim ledger entries, evidence items, and source records
to the shared ecosystem contracts for consumption by onto-canon6 and
other downstream projects.
"""

from __future__ import annotations

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


__all__ = [
    "claim_ledger_to_shared",
    "evidence_to_shared",
    "source_to_shared",
]
