"""Tests for analyst-output anonymization."""

from __future__ import annotations

from grounded_research.anonymize import scrub_analyst_run, scrub_identity_markers
from grounded_research.models import AnalystRun, Counterargument, RawClaim, Recommendation


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
