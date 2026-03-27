"""Tests for Tyler Stage 2 adapter surfaces."""

from __future__ import annotations

from datetime import datetime, timezone

from grounded_research.models import EvidenceBundle, EvidenceItem, ResearchQuestion, SourceRecord
from grounded_research.tyler_v1_adapters import current_bundle_to_tyler_evidence_package
from grounded_research.tyler_v1_models import DecompositionResult, ResearchPlan, StageSummary, SubQuestion


def _stage_summary(stage_name: str) -> StageSummary:
    return StageSummary(
        stage_name=stage_name,
        goal="goal",
        key_findings=["k1", "k2", "k3"],
        decisions_made=["d1"],
        outcome="outcome",
        reasoning="reasoning",
    )


def _tyler_decomposition() -> DecompositionResult:
    return DecompositionResult(
        core_question="What is the current evidence?",
        sub_questions=[
            SubQuestion(
                id="Q-1",
                question="What did pilot A show?",
                type="empirical",
                research_priority="high",
                search_guidance="official reports and evaluations",
            ),
            SubQuestion(
                id="Q-2",
                question="How should we interpret mixed findings?",
                type="interpretive",
                research_priority="medium",
                search_guidance="reviews and critiques",
            ),
        ],
        optimization_axes=["employment vs broader welfare"],
        research_plan=ResearchPlan(
            what_to_verify=["employment effect"],
            critical_source_types=["official docs", "academic"],
            falsification_targets=["contradictory RCT result", "N/A"],
        ),
        stage_summary=_stage_summary("Stage 1: Intake & Decomposition"),
    )


def test_current_bundle_to_tyler_evidence_package_groups_by_sub_question() -> None:
    bundle = EvidenceBundle(
        question=ResearchQuestion(text="What is the current evidence?"),
        sources=[
            SourceRecord(
                id="S-1",
                url="https://example.com/a",
                title="Pilot A",
                source_type="academic",
                quality_tier="authoritative",
                published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                retrieved_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
            ),
            SourceRecord(
                id="S-2",
                url="https://example.com/b",
                title="Commentary",
                source_type="news",
                quality_tier="reliable",
                published_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
                retrieved_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
            ),
        ],
        evidence=[
            EvidenceItem(
                id="E-1",
                source_id="S-1",
                content="Pilot A found a 2 percentage point decline in employment.",
                content_type="quotation",
                sub_question_ids=["Q-1"],
            ),
            EvidenceItem(
                id="E-2",
                source_id="S-2",
                content="Interpretation remains contested across analysts.",
                content_type="text",
                sub_question_ids=["Q-2"],
            ),
        ],
        gaps=[],
    )

    package = current_bundle_to_tyler_evidence_package(bundle, _tyler_decomposition())

    assert len(package.sub_question_evidence) == 2
    q1 = next(sqe for sqe in package.sub_question_evidence if sqe.sub_question_id == "Q-1")
    q2 = next(sqe for sqe in package.sub_question_evidence if sqe.sub_question_id == "Q-2")

    assert len(q1.sources) == 1
    assert q1.sources[0].quality_score == 0.9
    assert q1.sources[0].key_findings[0].evidence_label.value == "vendor_documented"
    assert q1.sources[0].key_findings[0].original_quote == "Pilot A found a 2 percentage point decline in employment."
    assert q1.meets_sufficiency is False
    assert len(q2.sources) == 1
    assert q2.sources[0].key_findings[0].evidence_label.value == "empirically_observed"
    assert package.stage_summary.stage_name == "Stage 2: Broad Retrieval & Evidence Normalization"
