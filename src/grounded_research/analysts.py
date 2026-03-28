"""Independent Tyler-native analyst execution.

The live Stage 3 path emits canonical `AnalysisObject`s plus narrow execution
traces. Older current-shape analyst execution was removed to keep one
production runtime vocabulary in `main`.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from grounded_research.config import (
    get_budget,
    get_model,
    load_config,
)
from grounded_research.models import EvidenceBundle, Stage3AttemptTrace
from grounded_research.runtime_policy import get_request_timeout
from grounded_research.tyler_v1_adapters import normalize_tyler_analysis_object
from grounded_research.tyler_v1_models import AnalysisObject, DecompositionResult as TylerDecompositionResult, EvidencePackage as TylerEvidencePackage

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


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
