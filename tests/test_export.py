"""Tests for export-layer runtime policy and repair behavior."""

from __future__ import annotations

import pytest

from grounded_research.export import generate_report, render_long_report
from grounded_research.models import (
    AnalystRun,
    Claim,
    ClaimLedger,
    Dispute,
    EvidenceBundle,
    EvidenceItem,
    PipelineState,
    QuestionDecomposition,
    ResearchQuestion,
    SourceRecord,
    SubQuestion,
)


@pytest.mark.asyncio
async def test_generate_report_passes_configured_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Structured synthesis should use the configured finite request timeout."""
    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, timeout):
        assert task == "report_synthesis"
        assert timeout == 240
        return response_model(
            title="Test Report",
            question="What is the evidence?",
            recommendation="Recommendation citing C-1.",
            cited_claim_ids=["C-1"],
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)

    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What is the evidence?"),
        evidence_bundle=EvidenceBundle(
            question=ResearchQuestion(text="What is the evidence?"),
            sources=[
                SourceRecord(
                    id="S-1",
                    url="https://example.com",
                    title="Source",
                    quality_tier="reliable",
                )
            ],
            evidence=[
                EvidenceItem(
                    id="E-1",
                    source_id="S-1",
                    content="Evidence content",
                    content_type="text",
                )
            ],
        ),
        claim_ledger=ClaimLedger(
            claims=[
                Claim(
                    id="C-1",
                    statement="A grounded claim.",
                    source_raw_claim_ids=["RC-1"],
                    analyst_sources=["Alpha"],
                    evidence_ids=["E-1"],
                    confidence="high",
                )
            ],
            disputes=[],
            arbitration_results=[],
        ),
    )

    report = await generate_report(state, trace_id="trace-1", max_budget=0.5)

    assert report.cited_claim_ids == ["C-1"]


@pytest.mark.asyncio
async def test_generate_report_repairs_grounding_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Structured synthesis should retry once when grounding validation fails."""
    calls: list[list[dict[str, str]]] = []

    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, timeout):
        calls.append(messages)
        if len(calls) == 1:
            return response_model(
                title="Test Report",
                question="What is the evidence?",
                recommendation="Recommendation citing C-1.",
                disagreement_summary="No major disagreements.",
                cited_claim_ids=["C-1"],
            ), {}
        return response_model(
            title="Test Report",
            question="What is the evidence?",
            recommendation="Recommendation citing C-1.",
            disagreement_summary="Unresolved dispute D-1 concerns whether the study generalizes.",
            cited_claim_ids=["C-1"],
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)

    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What is the evidence?"),
        evidence_bundle=EvidenceBundle(
            question=ResearchQuestion(text="What is the evidence?"),
            sources=[
                SourceRecord(
                    id="S-1",
                    url="https://example.com",
                    title="Source",
                    quality_tier="reliable",
                )
            ],
            evidence=[
                EvidenceItem(
                    id="E-1",
                    source_id="S-1",
                    content="Evidence content",
                    content_type="text",
                )
            ],
        ),
        claim_ledger=ClaimLedger(
            claims=[
                Claim(
                    id="C-1",
                    statement="A grounded claim.",
                    source_raw_claim_ids=["RC-1"],
                    analyst_sources=["Alpha"],
                    evidence_ids=["E-1"],
                    confidence="high",
                ),
                Claim(
                    id="C-2",
                    statement="A conflicting grounded claim.",
                    source_raw_claim_ids=["RC-2"],
                    analyst_sources=["Beta"],
                    evidence_ids=["E-1"],
                    confidence="medium",
                )
            ],
            disputes=[
                Dispute(
                    id="D-1",
                    claim_ids=["C-1", "C-2"],
                    dispute_type="interpretive_conflict",
                    route="arbitrate",
                    description="Generalization dispute.",
                    severity="notable",
                    resolved=False,
                )
            ],
            arbitration_results=[],
        ),
    )

    report = await generate_report(state, trace_id="trace-1", max_budget=0.5)

    assert len(calls) == 2
    assert "Repair Feedback" in calls[1][1]["content"]
    assert "D-1" in report.disagreement_summary


@pytest.mark.asyncio
async def test_render_long_report_repairs_placeholder_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Long-report synthesis should retry once when placeholder tokens appear."""
    calls: list[list[dict[str, str]]] = []
    outputs = [
        "## Broader Implications\nA macro effect could be X-Y% of labor input.",
        "## Reconciling the apparent contradictions\nThe evidence does not support a quantified aggregate estimate.",
    ]

    class FakeResult:
        def __init__(self, content: str) -> None:
            self.content = content

    async def fake_acall_llm(model, messages, task, trace_id, timeout, max_budget, fallback_models):
        calls.append(messages)
        return FakeResult(outputs[len(calls) - 1])

    monkeypatch.setattr("llm_client.acall_llm", fake_acall_llm)

    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What is the evidence?"),
        evidence_bundle=EvidenceBundle(
            question=ResearchQuestion(text="What is the evidence?"),
            sources=[
                SourceRecord(
                    id="S-1",
                    url="https://example.com",
                    title="Source",
                    quality_tier="reliable",
                )
            ],
            evidence=[
                EvidenceItem(
                    id="E-1",
                    source_id="S-1",
                    content="Evidence content",
                    content_type="text",
                )
            ],
        ),
        claim_ledger=ClaimLedger(
            claims=[
                Claim(
                    id="C-1",
                    statement="A grounded claim.",
                    source_raw_claim_ids=["RC-1"],
                    analyst_sources=["Alpha"],
                    evidence_ids=["E-1"],
                    confidence="high",
                )
            ],
            disputes=[],
            arbitration_results=[],
        ),
    )

    markdown = await render_long_report(state, trace_id="trace-1", max_budget=0.5)

    assert len(calls) == 2
    assert "Repair Feedback" in calls[1][1]["content"]
    assert "X-Y" not in markdown


@pytest.mark.asyncio
async def test_render_long_report_uses_sectioned_path_for_thorough_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Thorough-mode long reports should use section composition when the target is large."""
    calls: list[list[dict[str, str]]] = []

    class FakeResult:
        def __init__(self, content: str) -> None:
            self.content = content

    outputs = [
        "# Title\n\n## Executive summary\nIntro.\n\n## The core question and why it matters\nFrame.\n\n## The key distinctions\n- A\n- B",
        "## Fiscal feasibility versus labor response\nSection one.",
        "## Pilot design versus general-equilibrium limits\nSection two.",
        "## Distributional effects and heterogeneity\nSection three.",
        "## Broader implications\nImplications.\n\n## Verdict\nVerdict.\n\n## Alternatives and when to choose them\nAlternative.\n\n## What would change this recommendation\nCondition.\n\n## Closing summary\nClose.",
    ]

    async def fake_acall_llm(model, messages, task, trace_id, timeout, max_budget, fallback_models):
        calls.append(messages)
        return FakeResult(outputs[len(calls) - 1])

    monkeypatch.setattr("llm_client.acall_llm", fake_acall_llm)
    monkeypatch.setattr("grounded_research.export.get_model", lambda task: "test-model")
    monkeypatch.setattr("grounded_research.export.get_fallback_models", lambda task: None)
    monkeypatch.setattr("grounded_research.config.load_config", lambda: {"synthesis_mode": "analytical", "depth": "thorough"})
    monkeypatch.setattr("grounded_research.config.get_depth_config", lambda: {"synthesis_word_target": "10,000-15,000"})
    monkeypatch.setattr(
        "grounded_research.export.get_export_policy_config",
        lambda: {
            "sectioned_synthesis_min_word_target": 9000,
            "sectioned_synthesis_max_distinction_sections": 4,
            "sectioned_synthesis_enabled_depths": ["thorough"],
        },
    )

    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What is the evidence?"),
        evidence_bundle=EvidenceBundle(
            question=ResearchQuestion(text="What is the evidence?"),
            sources=[
                SourceRecord(
                    id="S-1",
                    url="https://example.com",
                    title="Source",
                    quality_tier="reliable",
                )
            ],
            evidence=[
                EvidenceItem(
                    id="E-1",
                    source_id="S-1",
                    content="Evidence content",
                    content_type="text",
                )
            ],
        ),
        claim_ledger=ClaimLedger(
            claims=[
                Claim(
                    id="C-1",
                    statement="A grounded claim.",
                    source_raw_claim_ids=["RC-1"],
                    analyst_sources=["Alpha"],
                    evidence_ids=["E-1"],
                    confidence="high",
                )
            ],
            disputes=[],
            arbitration_results=[],
        ),
    )
    decomposition = QuestionDecomposition(
        core_question="What is the evidence?",
        sub_questions=[
            SubQuestion(text="How do labor effects vary by pilot design?", type="comparative", falsification_target="No variation by design."),
            SubQuestion(text="How do fiscal constraints change the labor story?", type="causal", falsification_target="No meaningful fiscal constraint effect."),
        ],
        optimization_axes=[
            "Fiscal feasibility versus labor response",
            "Pilot design versus general-equilibrium limits",
            "Distributional effects and heterogeneity",
        ],
        research_plan="Plan",
    )

    markdown = await render_long_report(
        state,
        trace_id="trace-1",
        max_budget=1.0,
        decomposition=decomposition,
    )

    assert len(calls) == 5
    assert "# Title" in markdown
    assert "## Fiscal feasibility versus labor response" in markdown
    assert "## Verdict" in markdown
    assert "Section Mode" in calls[0][0]["content"]


@pytest.mark.asyncio
async def test_render_long_report_standard_mode_keeps_single_call_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Standard mode should keep the existing single-call rendering path."""
    calls: list[list[dict[str, str]]] = []

    class FakeResult:
        def __init__(self, content: str) -> None:
            self.content = content

    async def fake_acall_llm(model, messages, task, trace_id, timeout, max_budget, fallback_models):
        calls.append(messages)
        return FakeResult("## Broader Implications\nSingle-call report.")

    monkeypatch.setattr("llm_client.acall_llm", fake_acall_llm)
    monkeypatch.setattr("grounded_research.export.get_model", lambda task: "test-model")
    monkeypatch.setattr("grounded_research.export.get_fallback_models", lambda task: None)
    monkeypatch.setattr("grounded_research.config.load_config", lambda: {"synthesis_mode": "analytical", "depth": "standard"})
    monkeypatch.setattr("grounded_research.config.get_depth_config", lambda: {"synthesis_word_target": "5,000-6,000"})
    monkeypatch.setattr(
        "grounded_research.export.get_export_policy_config",
        lambda: {
            "sectioned_synthesis_min_word_target": 9000,
            "sectioned_synthesis_max_distinction_sections": 4,
            "sectioned_synthesis_enabled_depths": ["thorough"],
        },
    )

    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What is the evidence?"),
        evidence_bundle=EvidenceBundle(
            question=ResearchQuestion(text="What is the evidence?"),
            sources=[],
            evidence=[],
        ),
        claim_ledger=ClaimLedger(claims=[], disputes=[], arbitration_results=[]),
    )

    markdown = await render_long_report(state, trace_id="trace-1", max_budget=0.5)

    assert len(calls) == 1
    assert markdown == "## Broader Implications\nSingle-call report."


def test_successful_analyst_run_requires_counterarguments() -> None:
    """Successful analyst outputs must carry at least one counterargument."""
    with pytest.raises(ValueError):
        AnalystRun(
            analyst_label="Alpha",
            model="openrouter/openai/gpt-5-nano",
            frame="verification_first",
            summary="A successful run without counterarguments should fail validation.",
        )


def test_failed_analyst_run_allows_empty_counterarguments() -> None:
    """Failed analyst trace artifacts should not require semantic counterarguments."""
    result = AnalystRun(
        analyst_label="Alpha",
        model="openrouter/openai/gpt-5-nano",
        frame="verification_first",
        error="rate limit",
    )

    assert result.counterarguments == []
    assert not result.succeeded
