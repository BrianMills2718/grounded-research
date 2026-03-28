"""Independent analyst execution.

Legacy analyst mode still returns `AnalystRun`, but the live Tyler-native Stage
3 path emits canonical `AnalysisObject`s plus narrow execution traces. Analysts
never see each other's outputs.
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, timezone
from pathlib import Path

from grounded_research.config import (
    get_analysis_coverage_config,
    get_budget,
    get_depth_config,
    get_model,
    load_config,
)
from grounded_research.models import AnalystRun, EvidenceBundle, Stage3AttemptTrace
from grounded_research.runtime_policy import get_request_timeout
from grounded_research.tyler_v1_adapters import normalize_tyler_analysis_object
from grounded_research.tyler_v1_models import AnalysisObject, DecompositionResult as TylerDecompositionResult, EvidencePackage as TylerEvidencePackage

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LOG = logging.getLogger(__name__)


def _render_analyst_prompt(
    bundle: EvidenceBundle,
    frame: str,
    decomposition: "QuestionDecomposition | None" = None,
    claim_target: int = 0,
    coverage_retry_note: str = "",
) -> list[dict[str, str]]:
    """Render the analyst prompt template with optional decomposition context."""
    from llm_client import render_prompt

    # Pass sub-questions, axes, and ambiguous terms if decomposition is available
    sub_questions = []
    optimization_axes = []
    ambiguous_terms = []
    if decomposition is not None:
        sub_questions = [sq.model_dump() for sq in decomposition.sub_questions]
        optimization_axes = decomposition.optimization_axes
        ambiguous_terms = [at.model_dump() for at in decomposition.ambiguous_terms]

    return render_prompt(
        str(_PROJECT_ROOT / "prompts" / "analyst.yaml"),
        question=bundle.question.model_dump(),
        source_records=[s.model_dump(mode="json") for s in bundle.sources],
        evidence=[e.model_dump() for e in bundle.evidence],
        frame=frame,
        sub_questions=sub_questions,
        optimization_axes=optimization_axes,
        ambiguous_terms=ambiguous_terms,
        claim_target=claim_target,
        source_count=len(bundle.sources),
        evidence_count=len(bundle.evidence),
        coverage_retry_note=coverage_retry_note,
    )


async def _call_analyst_once(
    model: str,
    label: str,
    bundle: EvidenceBundle,
    frame: str,
    trace_id: str,
    max_budget: float,
    decomposition: "QuestionDecomposition | None",
    claim_target: int,
    coverage_retry_note: str,
) -> AnalystRun:
    """Execute one analyst attempt with a specific prompt variant."""
    from llm_client import acall_llm_structured

    messages = _render_analyst_prompt(
        bundle=bundle,
        frame=frame,
        decomposition=decomposition,
        claim_target=claim_target,
        coverage_retry_note=coverage_retry_note,
    )
    from grounded_research.config import get_fallback_models

    result, _meta = await acall_llm_structured(
        model,
        messages,
        response_model=AnalystRun,
        task="analyst_reasoning",
        trace_id=trace_id,
        timeout=get_request_timeout("analyst"),
        max_budget=max_budget,
        fallback_models=get_fallback_models("analyst"),
    )
    result.analyst_label = label
    result.model = model
    result.frame = frame
    result.completed_at = datetime.now(timezone.utc)
    return result


def _should_retry_for_undercoverage(
    result: AnalystRun,
    bundle: EvidenceBundle,
    claim_target: int,
) -> bool:
    """Return whether a rich bundle should trigger one coverage retry."""
    if not result.succeeded:
        return False
    if claim_target <= 0:
        return False

    policy = get_analysis_coverage_config()
    if not bool(policy["analyst_retry_on_undercoverage"]):
        return False
    if len(bundle.evidence) < int(policy["analyst_retry_min_evidence_items"]):
        return False

    min_claims = max(
        1,
        math.ceil(claim_target * float(policy["analyst_retry_min_claim_ratio"])),
    )
    return len(result.claims) < min_claims


async def run_analyst(
    model: str,
    label: str,
    bundle: EvidenceBundle,
    frame: str,
    trace_id: str,
    max_budget: float,
    decomposition: "QuestionDecomposition | None" = None,
) -> AnalystRun:
    """Run a single analyst and return the structured result.

    On failure, returns an AnalystRun with error set rather than raising.
    This preserves the trace for debugging.
    """
    claim_target = int(get_depth_config().get("analyst_claim_target", 0))
    max_attempts = int(get_analysis_coverage_config()["analyst_retry_max_attempts"])
    try:
        result = await _call_analyst_once(
            model=model,
            label=label,
            bundle=bundle,
            frame=frame,
            trace_id=f"{trace_id}/{label}",
            max_budget=max_budget,
            decomposition=decomposition,
            claim_target=claim_target,
            coverage_retry_note="",
        )

        if _should_retry_for_undercoverage(result, bundle, claim_target) and max_attempts > 0:
            coverage_retry_note = (
                f"Your first pass returned {len(result.claims)} claims, which is below the "
                f"configured target of about {claim_target} for a rich bundle with "
                f"{len(bundle.sources)} sources and {len(bundle.evidence)} evidence items. "
                "Re-run with broader coverage across distinct named studies, pilots, "
                "programs, populations, and outcome patterns already present in the "
                "evidence. Do not repeat multiple variants of the same case while "
                "ignoring other major named cases."
            )
            retry_trace_id = f"{trace_id}/{label}/coverage_retry_1"
            try:
                retry_result = await _call_analyst_once(
                    model=model,
                    label=label,
                    bundle=bundle,
                    frame=frame,
                    trace_id=retry_trace_id,
                    max_budget=max_budget,
                    decomposition=decomposition,
                    claim_target=claim_target,
                    coverage_retry_note=coverage_retry_note,
                )
                return retry_result
            except Exception as retry_error:
                _LOG.warning(
                    "Coverage retry failed for analyst %s; preserving first result. error=%s",
                    label,
                    retry_error,
                )
        return result
    except Exception as e:
        return AnalystRun(
            analyst_label=label,
            model=model,
            frame=frame,
            error=str(e),
            completed_at=datetime.now(timezone.utc),
        )


async def run_analysts(
    bundle: EvidenceBundle,
    trace_id: str,
    models: list[str] | None = None,
    frames: list[str] | None = None,
    decomposition: "QuestionDecomposition | None" = None,
) -> list[AnalystRun]:
    """Run 3 independent analysts in parallel.

    Aborts loudly if fewer than analyst_min_successful succeed.
    Returns all results (including failures) for trace completeness.
    """
    config = load_config()
    if models is None:
        default_model = get_model("analyst")
        models = config.get("analyst_models", [default_model] * 3)
    if frames is None:
        frames = config.get("analyst_frames", ["general"] * 3)

    labels = ["Alpha", "Beta", "Gamma"]
    min_successful = int(get_budget("analyst_min_successful"))
    budget_per = get_budget("pipeline_max_budget_usd") / len(models)

    tasks = [
        run_analyst(model, label, bundle, frame, trace_id, budget_per, decomposition)
        for model, label, frame in zip(models, labels, frames)
    ]
    results = await asyncio.gather(*tasks)

    succeeded = [r for r in results if r.succeeded]
    if len(succeeded) < min_successful:
        failed = [r for r in results if not r.succeeded]
        errors = "; ".join(f"{r.analyst_label}: {r.error}" for r in failed)
        raise RuntimeError(
            f"Only {len(succeeded)}/{len(results)} analysts succeeded "
            f"(minimum {min_successful}). Errors: {errors}"
        )

    return list(results)


def _render_tyler_analyst_prompt(
    stage_1_result: TylerDecompositionResult,
    stage_2_result: TylerEvidencePackage,
    *,
    model_alias: str,
    reasoning_frame: str,
) -> list[dict[str, str]]:
    """Render Tyler's literal Stage 3 prompt."""
    from llm_client import render_prompt

    return render_prompt(
        str(_PROJECT_ROOT / "prompts" / "tyler_v1_analyst.yaml"),
        original_query=stage_1_result.core_question,
        stage_1=stage_1_result.model_dump(mode="json"),
        stage_2=stage_2_result.model_dump(mode="json"),
        model_alias=model_alias,
        reasoning_frame=reasoning_frame,
        response_schema_json=AnalysisObject.model_json_schema(),
    )


async def _call_tyler_analyst_once(
    *,
    model: str,
    analyst_label: str,
    model_alias: str,
    stage_1_result: TylerDecompositionResult,
    stage_2_result: TylerEvidencePackage,
    reasoning_frame: str,
    trace_id: str,
    max_budget: float,
    bundle: EvidenceBundle,
) -> tuple[AnalysisObject, Stage3AttemptTrace]:
    """Execute one Tyler-native Stage 3 analyst and return a narrow attempt trace."""
    from llm_client import acall_llm_structured
    from grounded_research.config import get_fallback_models

    messages = _render_tyler_analyst_prompt(
        stage_1_result,
        stage_2_result,
        model_alias=model_alias,
        reasoning_frame=reasoning_frame,
    )
    result, _meta = await acall_llm_structured(
        model,
        messages,
        response_model=AnalysisObject,
        task="analyst_reasoning_tyler_v1",
        trace_id=trace_id,
        timeout=get_request_timeout("analyst"),
        max_budget=max_budget,
        fallback_models=get_fallback_models("analyst"),
    )
    normalized = normalize_tyler_analysis_object(
        result,
        valid_source_ids={source.id for source in bundle.sources},
        model_alias=model_alias,
        reasoning_frame=reasoning_frame,
    )
    return normalized, Stage3AttemptTrace(
        analyst_label=analyst_label,
        model_alias=model_alias,
        model=model,
        frame=reasoning_frame,
        succeeded=True,
        claim_count=len(normalized.claims),
        completed_at=datetime.now(timezone.utc),
    )


async def run_analysts_tyler_v1(
    *,
    bundle: EvidenceBundle,
    stage_1_result: TylerDecompositionResult,
    stage_2_result: TylerEvidencePackage,
    trace_id: str,
    models: list[str] | None = None,
    frames: list[str] | None = None,
) -> tuple[list[AnalysisObject], dict[str, str], list[Stage3AttemptTrace]]:
    """Run the live Tyler Stage 3 path and return canonical outputs plus attempt traces."""
    config = load_config()
    if models is None:
        default_model = get_model("analyst")
        models = config.get("analyst_models", [default_model] * 3)
    if frames is None:
        frames = config.get("analyst_frames", ["general"] * 3)

    labels = ["Alpha", "Beta", "Gamma"]
    aliases = ["A", "B", "C"]
    min_successful = int(get_budget("analyst_min_successful"))
    budget_per = get_budget("pipeline_max_budget_usd") / len(models)
    alias_mapping = {label: alias for label, alias in zip(labels, aliases)}

    async def _run_one(model: str, label: str, alias: str, frame: str) -> tuple[AnalysisObject | None, Stage3AttemptTrace]:
        try:
            analysis, attempt_trace = await _call_tyler_analyst_once(
                model=model,
                analyst_label=label,
                model_alias=alias,
                stage_1_result=stage_1_result,
                stage_2_result=stage_2_result,
                reasoning_frame=frame if frame in {"step_back_abstraction", "structured_decomposition", "verification_first"} else "verification_first",
                trace_id=f"{trace_id}/{label}",
                max_budget=budget_per,
                bundle=bundle,
            )
            return analysis, attempt_trace
        except Exception as exc:
            return None, Stage3AttemptTrace(
                analyst_label=label,
                model_alias=alias,
                model=model,
                frame=frame,
                succeeded=False,
                error=str(exc),
                completed_at=datetime.now(timezone.utc),
            )

    results = await asyncio.gather(*[
        _run_one(model, label, alias, frame)
        for model, label, alias, frame in zip(models, labels, aliases, frames)
    ])
    analyses = [analysis for analysis, attempt_trace in results if analysis is not None]
    attempt_traces = [attempt_trace for _, attempt_trace in results]

    succeeded = [run for run in attempt_traces if run.succeeded]
    if len(succeeded) < min_successful:
        failed = [r for r in attempt_traces if not r.succeeded]
        errors = "; ".join(f"{r.analyst_label}: {r.error}" for r in failed)
        raise RuntimeError(
            f"Only {len(succeeded)}/{len(attempt_traces)} analysts succeeded "
            f"(minimum {min_successful}). Errors: {errors}"
        )

    return analyses, alias_mapping, attempt_traces
