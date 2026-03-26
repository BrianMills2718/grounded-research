"""Tests for evidence compression coverage guarantees."""

from __future__ import annotations

from grounded_research.compress import compress_evidence
from grounded_research.models import EvidenceBundle, EvidenceItem, ResearchQuestion, SourceRecord


def test_compress_evidence_preserves_multi_tag_sub_question_coverage() -> None:
    """A multi-tag evidence item should satisfy coverage for every tagged sub-question."""
    bundle = EvidenceBundle(
        question=ResearchQuestion(text="What do UBI pilots show?"),
        sources=[
            SourceRecord(
                id="S-1",
                url="https://example.com/1",
                title="Authoritative report",
                quality_tier="authoritative",
            ),
            SourceRecord(
                id="S-2",
                url="https://example.com/2",
                title="Reliable follow-up",
                quality_tier="reliable",
            ),
        ],
        evidence=[
            EvidenceItem(
                id="E-1",
                source_id="S-1",
                content="Shared evidence relevant to labor and poverty outcomes.",
                sub_question_ids=["SQ-1", "SQ-2"],
            ),
            EvidenceItem(
                id="E-2",
                source_id="S-2",
                content="Extra evidence only about labor.",
                sub_question_ids=["SQ-1"],
            ),
            EvidenceItem(
                id="E-3",
                source_id="S-2",
                content="Extra evidence only about poverty.",
                sub_question_ids=["SQ-2"],
            ),
        ],
    )

    removed = compress_evidence(bundle, threshold=1)

    assert removed == 2
    assert [item.id for item in bundle.evidence] == ["E-1"]
    assert bundle.evidence[0].sub_question_ids == ["SQ-1", "SQ-2"]


def test_evidence_item_accepts_legacy_single_sub_question_field() -> None:
    """Legacy traces with one sub-question tag should upgrade on read."""
    item = EvidenceItem.model_validate(
        {
            "id": "E-1",
            "source_id": "S-1",
            "content": "Legacy evidence",
            "sub_question_id": "SQ-legacy",
        }
    )

    assert item.sub_question_ids == ["SQ-legacy"]
