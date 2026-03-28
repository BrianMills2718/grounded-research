"""Tests for export-layer runtime policy and repair behavior."""

from __future__ import annotations

import pytest

from grounded_research.export import generate_report, generate_tyler_synthesis_report, render_long_report
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
from grounded_research.tyler_v1_models import (
    ClaimExtractionResult as TylerClaimExtractionResult,
    ClaimLedgerEntry,
    ClaimStatus as TylerClaimStatus,
    ConfidenceAssessment,
    DisagreementMapEntry,
    EvidenceLabel,
    EvidencePackage,
    DisputeType,
    EvidenceTrailEntry,
    Finding,
    KeyAssumption,
    PreservedAlternative,
    ResearchPlan,
    Source,
    StageSummary,
    SubQuestionEvidence,
    SynthesisReport,
    Tradeoff,
    VerificationResult,
    DecompositionResult,
    SubQuestion as TylerSubQuestion,
)


def _tyler_report() -> SynthesisReport:
    return SynthesisReport(
        executive_recommendation="Recommendation based on C-1.",
        conditions_of_validity=["If C-1 flips, reconsider."],
        decision_relevant_tradeoffs=[Tradeoff(if_optimize_for="stability", then_recommend="Choose the stable option.")],
        disagreement_map=[
            DisagreementMapEntry(
                dispute_id="D-1",
                type=DisputeType.INTERPRETIVE,
                summary="Interpretive split",
                resolution="Resolved conservatively.",
                action_taken="Stage 5 arbitration",
                chosen_interpretation="Conservative",
            )
        ],
        preserved_alternatives=[
            PreservedAlternative(
                alternative="Aggressive option",
                conditions_for_preference="Use if upside dominates downside.",
                supporting_claims=["C-2"],
            )
        ],
        key_assumptions=[KeyAssumption(assumption_id="A-1", statement="Assumption one.", if_wrong="Recommendation weakens.")],
        confidence_assessment=[ConfidenceAssessment(claim_summary="C-1", confidence="medium", basis="Evidence is decent.")],
        process_summary=[
            StageSummary(
                stage_name="Stage 1",
                goal="goal",
                key_findings=["k1", "k2", "k3"],
                decisions_made=["d1"],
                outcome="outcome",
                reasoning="reasoning",
            )
        ],
        claim_ledger_excerpt=[
            {
                "claim_id": "C-1",
                "statement": "Primary claim",
                "final_status": "verified",
                "resolution_path": "Stage 5 supported it.",
            }
        ],
        evidence_trail=[
            EvidenceTrailEntry(
                source_id="S-1",
                url="https://example.com/source",
                quality_score=0.9,
                key_contribution="Supports C-1",
                conflicts_resolved=["D-1"],
            )
        ],
        evidence_gaps=["Need a larger sample."],
        reasoning="Reasoning",
        stage_summary=StageSummary(
            stage_name="Stage 6",
            goal="goal",
            key_findings=["k1", "k2", "k3"],
            decisions_made=["d1"],
            outcome="outcome",
            reasoning="reasoning",
        ),
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
async def test_generate_report_projects_from_tyler_stage6_when_available() -> None:
    """Tyler Stage 6 should become the source of truth for the structured report."""
    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What should we do?"),
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
        tyler_stage_6_result=_tyler_report(),
    )

    report = await generate_report(state, trace_id="trace-1", max_budget=0.5)

    assert report.cited_claim_ids == ["C-1"]
    assert "D-1" in report.disagreement_summary


@pytest.mark.asyncio
async def test_generate_report_preserves_unresolved_disputes_when_tyler_stage6_omits_map() -> None:
    """Projected FinalReport must keep unresolved disputes visible for grounding checks."""
    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What should we do?"),
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
                    statement="A competing grounded claim.",
                    source_raw_claim_ids=["RC-2"],
                    analyst_sources=["Beta"],
                    evidence_ids=["E-1"],
                    confidence="medium",
                )
            ],
            disputes=[
                Dispute(
                    id="D-2",
                    claim_ids=["C-1", "C-2"],
                    dispute_type="interpretive_conflict",
                    route="arbitrate",
                    description="Interpretation remains unresolved.",
                    severity="decision_critical",
                    resolved=False,
                    resolution_summary="Need to preserve the unresolved interpretation split.",
                )
            ],
            arbitration_results=[],
        ),
        tyler_stage_6_result=_tyler_report().model_copy(update={"disagreement_map": []}),
    )

    report = await generate_report(state, trace_id="trace-1", max_budget=0.5)

    assert "D-2" in (report.disagreement_summary or "")
    assert "unresolved" in (report.disagreement_summary or "")


@pytest.mark.asyncio
async def test_generate_report_filters_ungrounded_tyler_stage6_claims() -> None:
    """Tyler Stage 6 projected citations must be filtered to grounded current claims."""
    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What should we do?"),
        claim_ledger=ClaimLedger(
            claims=[
                Claim(
                    id="C-1",
                    statement="An ungrounded projected claim.",
                    source_raw_claim_ids=["RC-1"],
                    analyst_sources=["Alpha"],
                    evidence_ids=[],
                    confidence="medium",
                )
            ],
            disputes=[],
            arbitration_results=[],
        ),
        tyler_stage_6_result=_tyler_report(),
    )

    report = await generate_report(state, trace_id="trace-1", max_budget=0.5)

    assert report.cited_claim_ids == []


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
async def test_render_long_report_uses_tyler_stage6_markdown_when_available() -> None:
    """Tyler Stage 6 should render directly to markdown without another LLM call."""
    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What should we do?"),
        tyler_stage_6_result=_tyler_report(),
    )

    markdown = await render_long_report(state, trace_id="trace-1", max_budget=0.5)

    assert "## Executive Recommendation" in markdown
    assert "C-1" in markdown


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


@pytest.mark.asyncio
async def test_generate_tyler_synthesis_report_prefers_persisted_tyler_stage_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 6 should not rebuild Tyler Stage 1/2 when state already has them."""

    def stage_summary(stage_name: str) -> StageSummary:
        return StageSummary(
            stage_name=stage_name,
            goal="goal",
            key_findings=["k1", "k2", "k3"],
            decisions_made=["d1"],
            outcome="outcome",
            reasoning="reasoning",
        )

    async def fail_decompose(*args, **kwargs):
        raise AssertionError("should not re-decompose")

    monkeypatch.setattr("grounded_research.decompose.decompose_question_tyler_v1", fail_decompose)
    monkeypatch.setattr(
        "grounded_research.export.current_bundle_to_tyler_evidence_package",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not rebuild stage 2")),
    )

    async def fake_acall_llm_structured(*args, **kwargs):
        response_model = kwargs["response_model"]
        return response_model(
            executive_recommendation="Recommendation.",
            conditions_of_validity=["Condition."],
            decision_relevant_tradeoffs=[{"if_optimize_for": "Speed", "then_recommend": "A"}],
            disagreement_map=[],
            preserved_alternatives=[],
            key_assumptions=[],
            confidence_assessment=[{"claim_summary": "Summary", "confidence": "medium", "basis": "Basis"}],
            process_summary=[stage_summary("Stage 6").model_dump(mode="json")],
            claim_ledger_excerpt=[{"claim_id": "C-1", "statement": "Claim", "final_status": "verified", "resolution_path": "Stage 5"}],
            evidence_trail=[{"source_id": "S-1", "url": "https://example.com", "quality_score": 0.9, "key_contribution": "Contribution"}],
            evidence_gaps=[],
            reasoning="Reasoning",
            stage_summary=stage_summary("Stage 6").model_dump(mode="json"),
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)
    monkeypatch.setattr("llm_client.render_prompt", lambda *args, **kwargs: [{"role": "user", "content": "prompt"}])
    monkeypatch.setattr("grounded_research.export.get_model", lambda task: "test-model")
    monkeypatch.setattr("grounded_research.export.get_fallback_models", lambda task: None)

    state = PipelineState(
        run_id="run-1",
        question=ResearchQuestion(text="What is the evidence?"),
        evidence_bundle=EvidenceBundle(
            question=ResearchQuestion(text="What is the evidence?"),
            sources=[SourceRecord(id="S-1", url="https://example.com", title="Source", quality_tier="authoritative")],
            evidence=[EvidenceItem(id="E-1", source_id="S-1", content="Evidence", content_type="text")],
            gaps=[],
        ),
        tyler_stage_1_result=DecompositionResult(
            core_question="What is the evidence?",
            sub_questions=[
                TylerSubQuestion(id="Q-1", question="Q1", type="empirical", research_priority="high", search_guidance="docs"),
                TylerSubQuestion(id="Q-2", question="Q2", type="interpretive", research_priority="medium", search_guidance="critiques"),
            ],
            optimization_axes=["speed vs rigor"],
            research_plan=ResearchPlan(
                what_to_verify=["claim"],
                critical_source_types=["official docs"],
                falsification_targets=["contradiction"],
            ),
                stage_summary=StageSummary(
                    stage_name="Stage 1",
                    goal="goal",
                    key_findings=["k1", "k2", "k3"],
                    decisions_made=["d1"],
                    outcome="outcome",
                    reasoning="reasoning",
                ),
        ),
        tyler_stage_2_result=EvidencePackage(
            sub_question_evidence=[
                SubQuestionEvidence(
                    sub_question_id="Q-1",
                    sources=[
                        Source(
                            id="S-1",
                            url="https://example.com",
                            title="Source",
                            source_type="official_docs",
                            quality_score=0.9,
                            publication_date="2026-01-01",
                            retrieval_date="2026-03-27",
                            key_findings=[
                                Finding(
                                    finding="Finding",
                                    evidence_label=EvidenceLabel.VENDOR_DOCUMENTED,
                                    original_quote=None,
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
                stage_summary=StageSummary(
                    stage_name="Stage 2",
                    goal="goal",
                    key_findings=["k1", "k2", "k3"],
                    decisions_made=["d1"],
                    outcome="outcome",
                    reasoning="reasoning",
                ),
        ),
        tyler_stage_4_result=TylerClaimExtractionResult(
            claim_ledger=[
                ClaimLedgerEntry(
                    id="C-1",
                    statement="Claim",
                    source_models=["A"],
                    evidence_label=EvidenceLabel.VENDOR_DOCUMENTED,
                    source_references=["S-1"],
                    status=TylerClaimStatus.VERIFIED,
                    supporting_models=["A"],
                    contesting_models=[],
                    related_assumptions=[],
                )
            ],
            assumption_set=[],
            dispute_queue=[],
            statistics={
                "total_claims": 1,
                "total_assumptions": 0,
                "total_disputes": 0,
                "disputes_by_type": {},
                "decision_critical_disputes": 0,
                "claims_per_model": {"A": 1},
            },
                stage_summary=StageSummary(
                    stage_name="Stage 4",
                    goal="goal",
                    key_findings=["k1", "k2", "k3"],
                    decisions_made=["d1"],
                    outcome="outcome",
                    reasoning="reasoning",
                ),
        ),
        tyler_stage_5_result=VerificationResult(
            disputes_investigated=[],
            additional_sources=[],
            updated_claim_ledger=[
                ClaimLedgerEntry(
                    id="C-1",
                    statement="Claim",
                    source_models=["A"],
                    evidence_label=EvidenceLabel.VENDOR_DOCUMENTED,
                    source_references=["S-1"],
                    status=TylerClaimStatus.VERIFIED,
                    supporting_models=["A"],
                    contesting_models=[],
                    related_assumptions=[],
                )
            ],
            updated_dispute_queue=[],
            search_budget={},
            rounds_used=0,
                stage_summary=StageSummary(
                    stage_name="Stage 5",
                    goal="goal",
                    key_findings=["k1", "k2", "k3"],
                    decisions_made=["d1"],
                    outcome="outcome",
                    reasoning="reasoning",
                ),
        ),
    )

    result = await generate_tyler_synthesis_report(state, decomposition=None, trace_id="trace-root")

    assert result.executive_recommendation == "Recommendation."


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
