"""Tests for fixture sidecar loading policy."""

from __future__ import annotations

from pathlib import Path

from engine import _load_fixture_sidecars
from grounded_research.models import QuestionDecomposition, SubQuestion
from grounded_research.tyler_v1_models import (
    DecompositionResult,
    EvidencePackage,
    ResearchPlan,
    StageSummary,
    SubQuestion as TylerSubQuestion,
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


def _write_fixture_bundle(tmp_path: Path) -> Path:
    fixture_path = tmp_path / "bundle.json"
    fixture_path.write_text("{}")
    return fixture_path


def _write_tyler_stage1(tmp_path: Path) -> None:
    result = DecompositionResult(
        core_question="What is the evidence?",
        sub_questions=[
            TylerSubQuestion(
                id="Q-1",
                question="What happened?",
                type="empirical",
                research_priority="high",
                search_guidance="docs",
            ),
            TylerSubQuestion(
                id="Q-2",
                question="How should we interpret it?",
                type="interpretive",
                research_priority="medium",
                search_guidance="reviews",
            ),
        ],
        optimization_axes=["axis"],
        research_plan=ResearchPlan(
            what_to_verify=["claim"],
            critical_source_types=["official docs"],
            falsification_targets=["contradiction", "n/a"],
        ),
        stage_summary=_stage_summary("Stage 1"),
    )
    (tmp_path / "tyler_stage_1.json").write_text(result.model_dump_json(indent=2))


def _write_tyler_stage2(tmp_path: Path) -> None:
    result = EvidencePackage(
        sub_question_evidence=[],
        total_queries_used=0,
        queries_per_sub_question={},
        stage_summary=_stage_summary("Stage 2"),
    )
    (tmp_path / "tyler_stage_2.json").write_text(result.model_dump_json(indent=2))


def _write_legacy_decomposition(path: Path) -> None:
    result = QuestionDecomposition(
        core_question="What is the evidence?",
        sub_questions=[
            SubQuestion(
                id="SQ-1",
                text="What happened?",
                type="factual",
                falsification_target="contradiction",
            ),
            SubQuestion(
                id="SQ-2",
                text="How should we interpret it?",
                type="evaluative",
                falsification_target="counter",
            ),
        ],
        optimization_axes=["axis"],
        research_plan="plan",
        ambiguous_terms=[],
    )
    path.write_text(result.model_dump_json(indent=2))


def test_fixture_sidecars_auto_detect_tyler_only(tmp_path: Path) -> None:
    fixture = _write_fixture_bundle(tmp_path)
    _write_tyler_stage1(tmp_path)
    _write_tyler_stage2(tmp_path)
    _write_legacy_decomposition(tmp_path / "decomposition.json")

    decomp, stage1, stage2 = _load_fixture_sidecars(fixture)

    assert decomp is None
    assert stage1 is not None
    assert stage2 is not None


def test_fixture_sidecars_load_legacy_decomposition_only_when_explicit(tmp_path: Path) -> None:
    fixture = _write_fixture_bundle(tmp_path)
    legacy_path = tmp_path / "decomposition.json"
    _write_legacy_decomposition(legacy_path)

    decomp, stage1, stage2 = _load_fixture_sidecars(
        fixture,
        decomposition_path=legacy_path,
    )

    assert decomp is not None
    assert decomp.sub_questions[0].id == "SQ-1"
    assert stage1 is None
    assert stage2 is None
