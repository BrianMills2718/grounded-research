"""Tests for Tyler-native Stage 3 runtime migration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from grounded_research.analysts import run_analysts_tyler_v1
from grounded_research.config import load_config
from grounded_research.models import EvidenceBundle, EvidenceItem, ResearchQuestion, SourceRecord
from grounded_research.tyler_v1_models import (
    AnalysisObject,
    ConfidenceLevel,
    CounterArgument,
    DecompositionResult,
    EvidenceLabel,
    EvidencePackage,
    Finding,
    ResearchPlan,
    Source,
    StageSummary,
    SubQuestion,
    SubQuestionEvidence,
)


def _stage_summary(stage_name: str) -> StageSummary:
    return StageSummary(
        stage_name=stage_name,
        goal="goal",
        key_findings=["k1", "k2", "k3"],
        decisions_made=["d1"],
        outcome="outcome",
        reasoning="reasoning",
    )


def _stage_1() -> DecompositionResult:
    return DecompositionResult(
        core_question="What should we recommend?",
        sub_questions=[
            SubQuestion(
                id="Q-1",
                question="What does the evidence show?",
                type="empirical",
                research_priority="high",
                search_guidance="official docs",
            ),
            SubQuestion(
                id="Q-2",
                question="How should it be interpreted?",
                type="interpretive",
                research_priority="medium",
                search_guidance="critiques",
            ),
        ],
        optimization_axes=["cost vs reliability"],
        research_plan=ResearchPlan(
            what_to_verify=["core claim"],
            critical_source_types=["official docs"],
            falsification_targets=["contradiction", "N/A"],
        ),
        stage_summary=_stage_summary("Stage 1: Intake & Decomposition"),
    )


def _stage_2() -> EvidencePackage:
    return EvidencePackage(
        sub_question_evidence=[
            SubQuestionEvidence(
                sub_question_id="Q-1",
                sources=[
                    Source(
                        id="S-1",
                        url="https://example.com/a",
                        title="Official Source",
                        source_type="official_docs",
                        quality_score=0.9,
                        publication_date="2026-01-01",
                        retrieval_date="2026-03-27",
                        key_findings=[
                            Finding(
                                finding="Benchmark shows 10% improvement.",
                                evidence_label=EvidenceLabel.VENDOR_DOCUMENTED,
                                original_quote="Benchmark shows 10% improvement.",
                            )
                        ],
                    )
                ],
                meets_sufficiency=False,
                gap_description="Only one source",
            )
        ],
        total_queries_used=4,
        queries_per_sub_question={"Q-1": 4, "Q-2": 4},
        stage_summary=_stage_summary("Stage 2: Broad Retrieval & Evidence Normalization"),
    )


def _bundle() -> EvidenceBundle:
    return EvidenceBundle(
        question=ResearchQuestion(text="What should we recommend?"),
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


@pytest.mark.asyncio
async def test_run_analysts_tyler_v1_returns_tyler_outputs_and_attempt_traces(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_acall_llm_structured(*args, **kwargs):
        response_model = kwargs["response_model"]
        return response_model(
            model_alias="bad",
            reasoning_frame="general",
            recommendation="Choose the benchmark winner.",
            claims=[
                {
                    "id": "bad-claim",
                    "statement": "The benchmark showed a 10% improvement.",
                    "evidence_label": "vendor_documented",
                    "source_references": ["S-1"],
                    "confidence": "high",
                }
            ],
            assumptions=[
                {
                    "id": "bad-assumption",
                    "statement": "The benchmark generalizes to production.",
                    "depends_on_claims": ["bad-claim"],
                    "if_wrong_impact": "Recommendation weakens.",
                }
            ],
            evidence_used=["S-1"],
            counter_argument={
                "argument": "The benchmark may not generalize to production.",
                "strongest_evidence_against": "Benchmark shows 10% improvement.",
                "counter_confidence": "medium",
            },
            falsification_conditions=["Production evidence contradicts the benchmark."],
            reasoning="The evidence supports the recommendation but may not generalize.",
            stage_summary=_stage_summary("Stage 3: Independent Candidate Generation").model_dump(mode="json"),
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr("llm_client.render_prompt", lambda *args, **kwargs: [{"role": "user", "content": "prompt"}])

    analyses, alias_mapping, attempts = await run_analysts_tyler_v1(
        bundle=_bundle(),
        stage_1_result=_stage_1(),
        stage_2_result=_stage_2(),
        trace_id="test/trace",
        models=["model-a", "model-b", "model-c"],
        frames=["verification_first", "structured_decomposition", "step_back_abstraction"],
    )

    assert len(analyses) == 3
    assert alias_mapping == {"Alpha": "A", "Beta": "B", "Gamma": "C"}
    assert analyses[0].model_alias == "A"
    assert analyses[0].claims[0].id == "C-1"
    assert len(attempts) == 3
    assert attempts[0].succeeded
    assert attempts[0].model_alias == "A"
    assert attempts[0].claim_count == 1


@pytest.mark.asyncio
async def test_run_analysts_tyler_v1_enforces_quality_floor_on_canonical_outputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 3 should reject schema-valid outputs that fail the quality floor."""

    async def fake_acall_llm_structured(*args, **kwargs):
        response_model = kwargs["response_model"]
        return response_model(
            model_alias="bad",
            reasoning_frame="general",
            recommendation="",
            claims=[],
            assumptions=[],
            evidence_used=["S-1"],
            counter_argument={
                "argument": "",
                "strongest_evidence_against": "",
                "counter_confidence": "medium",
            },
            falsification_conditions=["Production evidence contradicts the benchmark."],
            reasoning="Thin answer.",
            stage_summary=_stage_summary("Stage 3: Independent Candidate Generation").model_dump(mode="json"),
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr("llm_client.render_prompt", lambda *args, **kwargs: [{"role": "user", "content": "prompt"}])

    with pytest.raises(RuntimeError, match="Only 0/3 analysts succeeded"):
        await run_analysts_tyler_v1(
            bundle=_bundle(),
            stage_1_result=_stage_1(),
            stage_2_result=_stage_2(),
            trace_id="test/trace",
            models=["model-a", "model-b", "model-c"],
            frames=["verification_first", "structured_decomposition", "step_back_abstraction"],
        )


def test_tyler_stage3_primary_config_matches_recovery_contract() -> None:
    """The primary Stage 3 config should stay aligned with the recovery plan."""
    config_path = Path(__file__).resolve().parent.parent / "config" / "config.yaml"
    cfg = yaml.safe_load(config_path.read_text())

    assert len(cfg["analyst_models"]) == 3
    assert cfg["analyst_models"] == [
        "openrouter/openai/gpt-5.4",
        "openrouter/google/gemini-3.1-pro-preview",
        "openrouter/anthropic/claude-opus-4.6",
    ]
    assert cfg["analyst_frames"] == [
        "step_back_abstraction",
        "structured_decomposition",
        "verification_first",
    ]
