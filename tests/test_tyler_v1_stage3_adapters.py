"""Tests for Tyler Stage 3 adapter surfaces."""

from __future__ import annotations

from datetime import datetime, timezone

from grounded_research.models import (
    AnalystRun,
    Assumption,
    Counterargument,
    EvidenceBundle,
    EvidenceItem,
    RawClaim,
    Recommendation,
    ResearchQuestion,
    SourceRecord,
)
from grounded_research.tyler_v1_adapters import current_analyst_run_to_tyler_analysis


def test_current_analyst_run_to_tyler_analysis_maps_sources_and_counterargument() -> None:
    bundle = EvidenceBundle(
        question=ResearchQuestion(text="What is the best recommendation?"),
        sources=[
            SourceRecord(
                id="S-1",
                url="https://example.com/a",
                title="Official Source",
                source_type="academic",
                quality_tier="authoritative",
                published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                retrieved_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
            )
        ],
        evidence=[
            EvidenceItem(
                id="E-1",
                source_id="S-1",
                content="Benchmark shows 10% improvement.",
                content_type="quotation",
            )
        ],
    )
    run = AnalystRun(
        analyst_label="Alpha",
        model="openrouter/openai/gpt-5-nano",
        frame="verification_first",
        claims=[
            RawClaim(
                id="RC-1",
                statement="The benchmark showed a 10% improvement.",
                evidence_ids=["E-1"],
                confidence="high",
            )
        ],
        assumptions=[
            Assumption(
                id="A-1",
                statement="The benchmark generalizes to production.",
                basis="No contradictory production evidence was present.",
            )
        ],
        recommendations=[
            Recommendation(
                statement="Choose the benchmark winner.",
                supporting_claim_ids=["RC-1"],
                conditions="If production resembles the benchmark environment.",
            )
        ],
        counterarguments=[
            Counterargument(
                target="Choose the benchmark winner.",
                argument="The benchmark may not generalize to production.",
                evidence_ids=["E-1"],
            )
        ],
        summary="The evidence supports the recommendation but may not generalize.",
        completed_at=datetime.now(timezone.utc),
    )

    analysis = current_analyst_run_to_tyler_analysis(
        run=run,
        bundle=bundle,
        model_alias="A",
        reasoning_frame="verification_first",
    )

    assert analysis.model_alias == "A"
    assert analysis.reasoning_frame == "verification_first"
    assert analysis.claims[0].source_references == ["S-1"]
    assert analysis.claims[0].evidence_label.value == "vendor_documented"
    assert analysis.counter_argument.argument == "The benchmark may not generalize to production."
    assert analysis.counter_argument.strongest_evidence_against == "Benchmark shows 10% improvement."
    assert analysis.evidence_used == ["S-1"]
