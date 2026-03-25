"""Independent analyst execution.

Runs LLM analysts over shared evidence bundles. Each analyst produces
a structured AnalystRun with claims, assumptions, recommendations, and
counterarguments. Analysts never see each other's outputs.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from grounded_research.config import get_budget, get_model, load_config
from grounded_research.models import AnalystRun, EvidenceBundle

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _render_analyst_prompt(
    bundle: EvidenceBundle,
    frame: str,
    decomposition: "QuestionDecomposition | None" = None,
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
    )


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
    from llm_client import acall_llm_structured

    messages = _render_analyst_prompt(bundle, frame, decomposition)
    try:
        from grounded_research.config import get_fallback_models
        result, _meta = await acall_llm_structured(
            model,
            messages,
            response_model=AnalystRun,
            task="analyst_reasoning",
            trace_id=f"{trace_id}/{label}",
            max_budget=max_budget,
            fallback_models=get_fallback_models("analyst"),
        )
        result.analyst_label = label
        result.model = model
        result.frame = frame
        result.completed_at = datetime.now(timezone.utc)
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
