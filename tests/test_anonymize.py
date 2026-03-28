"""Tests for analyst-output anonymization."""

from __future__ import annotations

from grounded_research.anonymize import (
    scrub_analyst_run,
    scrub_identity_markers,
    scrub_tyler_analysis_object,
)
from grounded_research.models import AnalystRun, Counterargument, RawClaim, Recommendation
from grounded_research.tyler_v1_models import AnalysisObject, CounterArgument, StageSummary


def test_scrub_identity_markers_replaces_self_identification() -> None:
    """Self-identification phrases should be rewritten to analyst-neutral text."""
    cleaned, changed = scrub_identity_markers(
        "As an OpenAI model, I think the benchmark is weak. My training data suggests caution."
    )

    assert changed is True
    assert "OpenAI model" not in cleaned
    assert "training data" not in cleaned.lower()
    assert "As an analyst" in cleaned


def test_scrub_analyst_run_mutates_downstream_reused_fields() -> None:
    """Claim, recommendation, counterargument, and summary text should be scrubbed."""
    run = AnalystRun(
        analyst_label="Alpha",
        model="openrouter/openai/gpt-5-nano",
        frame="verification_first",
        claims=[
            RawClaim(
                statement="As Claude, I find the evidence mixed.",
                evidence_ids=["E-1"],
                confidence="medium",
                reasoning="My training data gives prior context, but the fresh evidence is thin.",
            )
        ],
        recommendations=[
            Recommendation(
                statement="I'm Gemini, so I would recommend waiting for stronger evidence.",
                conditions="As an Anthropic model, I would want a second benchmark.",
            )
        ],
        counterarguments=[
            Counterargument(
                target="As ChatGPT, I may be over-weighting the benchmark.",
                argument="As an OpenAI assistant, I might be too optimistic.",
                evidence_ids=["E-1"],
            )
        ],
        summary="As a Google model, I see unresolved disagreement.",
    )

    redactions = scrub_analyst_run(run)

    assert redactions
    assert "Claude" not in run.claims[0].statement
    assert "training data" not in run.claims[0].reasoning.lower()
    assert "Gemini" not in run.recommendations[0].statement
    assert "Anthropic model" not in run.recommendations[0].conditions
    assert "ChatGPT" not in run.counterarguments[0].target
    assert "OpenAI assistant" not in run.counterarguments[0].argument
    assert "Google model" not in run.summary


def test_scrub_tyler_analysis_object_mutates_stage3_fields() -> None:
    """Tyler Stage 3 artifacts should scrub self-identification before downstream reuse."""
    analysis = AnalysisObject(
        model_alias="A",
        reasoning_frame="verification_first",
        recommendation="As Gemini, I recommend waiting.",
        claims=[
            {
                "id": "C-1",
                "statement": "As Claude, the evidence is mixed.",
                "evidence_label": "vendor_documented",
                "source_references": ["S-1"],
                "confidence": "medium",
            }
        ],
        assumptions=[
            {
                "id": "A-1",
                "statement": "As ChatGPT, deployment will match the benchmark.",
                "depends_on_claims": ["C-1"],
                "if_wrong_impact": "My training data prior would be wrong.",
            }
        ],
        evidence_used=["S-1"],
        counter_argument=CounterArgument(
            argument="As an OpenAI assistant, I may be too optimistic.",
            strongest_evidence_against="As a Google model, the benchmark may not generalize.",
            counter_confidence="medium",
        ),
        falsification_conditions=["As an Anthropic model, I would change my view if production regressed."],
        reasoning="As an OpenAI model, I see unresolved disagreement.",
        stage_summary=StageSummary(
            stage_name="Stage 3",
            goal="goal",
            key_findings=["k1", "k2", "k3"],
            decisions_made=["d1"],
            outcome="outcome",
            reasoning="reasoning",
        ),
    )

    redactions = scrub_tyler_analysis_object(analysis)

    assert redactions
    assert "Gemini" not in analysis.recommendation
    assert "Claude" not in analysis.claims[0].statement
    assert "ChatGPT" not in analysis.assumptions[0].statement
    assert "training data" not in analysis.assumptions[0].if_wrong_impact.lower()
    assert "OpenAI assistant" not in analysis.counter_argument.argument
    assert "Google model" not in analysis.counter_argument.strongest_evidence_against
    assert "Anthropic model" not in analysis.falsification_conditions[0]
    assert "OpenAI model" not in analysis.reasoning
