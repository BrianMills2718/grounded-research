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


def _load_handoff_v1(data: dict) -> list[ClaimRecord]:
    """Load Tyler V1 format: claim_ledger.claims[] with confidence string."""
    claim_ledger = data.get("claim_ledger", {})
    raw_claims = claim_ledger.get("claims", [])
    evidence_by_id = {e["id"]: e for e in data.get("evidence", [])}

    records: list[ClaimRecord] = []
    for raw in raw_claims:
        confidence_str = str(raw.get("confidence", "medium")).lower()
        confidence_weights = {"high": 0.8, "medium": 0.5, "low": 0.2}
        score = confidence_weights.get(confidence_str, 0.5)

        confidence = ConfidenceScore(score=score, source="adjudication")
        status_str = str(raw.get("status", "initial")).lower()

        source_ids = []
        for eid in raw.get("evidence_ids", []):
            ev = evidence_by_id.get(eid)
            if ev and ev.get("source_id"):
                source_ids.append(ev["source_id"])
        seen: set[str] = set()
        unique_source_ids = [s for s in source_ids if not (s in seen or seen.add(s))]  # type: ignore[func-returns-value]

        records.append(ClaimRecord(
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
        ))
    return records


def _load_handoff_stage_based(data: dict) -> list[ClaimRecord]:
    """Load stage-based format: stage_5_verification_result.updated_claim_ledger[].

    Produced by the testing config and newer pipeline variants. Claim status
    ("supported", "contested", "unverified") drives confidence; evidence_label
    provides an additional signal via EVIDENCE_LABEL_WEIGHTS.
    """
    status_confidence: dict[str, float] = {
        "supported": 0.8,
        "corroborated": 0.9,
        "contested": 0.5,
        "unverified": 0.3,
        "refuted": 0.1,
        "initial": 0.5,
    }

    s5 = data.get("stage_5_verification_result", {})
    raw_claims = s5.get("updated_claim_ledger", [])

    records: list[ClaimRecord] = []
    for raw in raw_claims:
        status_str = str(raw.get("status", "unverified")).lower()
        label = str(raw.get("evidence_label", "")).lower()
        label_score = EVIDENCE_LABEL_WEIGHTS.get(label)

        # Take the minimum: evidence_label gives the source quality ceiling,
        # status gives the adjudication floor — a "contested" claim can't
        # exceed medium confidence regardless of evidence quality.
        status_score = status_confidence.get(status_str, 0.5)
        score = min(label_score, status_score) if label_score is not None else status_score

        confidence = ConfidenceScore(
            score=score,
            source="adjudication",
            evidence_label=label if label in EVIDENCE_LABEL_WEIGHTS else None,  # type: ignore[arg-type]
        )

        records.append(ClaimRecord(
            id=raw["id"],
            statement=raw["statement"],
            claim_type="fact_claim",
            status=status_str,  # type: ignore[arg-type]
            confidence=confidence,
            source_ids=list(raw.get("source_references", [])),
            supporting_models=list(raw.get("supporting_models", [])),
            contesting_models=list(raw.get("contesting_models", [])),
            is_provisional=bool(raw.get("is_provisional", True)),
            source_system="grounded-research",
        ))
    return records


def load_handoff_claims(handoff_path: str | Path) -> list[ClaimRecord]:
    """Load claims from a grounded-research handoff.json into shared ClaimRecords.

    Handles two formats:
    - Tyler V1: claim_ledger.claims[] with confidence string ("high"/"medium"/"low")
    - Stage-based: stage_5_verification_result.updated_claim_ledger[] with status field
    """
    import json

    handoff_path = Path(handoff_path)
    data = json.loads(handoff_path.read_text())

    if "claim_ledger" in data and data["claim_ledger"].get("claims"):
        return _load_handoff_v1(data)
    elif "stage_5_verification_result" in data:
        return _load_handoff_stage_based(data)
    else:
        return []


__all__ = [
    "claim_ledger_to_shared",
    "evidence_to_shared",
    "load_handoff_claims",
    "source_to_shared",
]
