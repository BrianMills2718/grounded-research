"""Question decomposition: break a research question into typed sub-questions.

Phase A of the v2 pipeline. Runs before evidence collection to focus
search queries per sub-question and give analysts structured context.
See ADR-0006 for design decisions.
"""

from __future__ import annotations

from pathlib import Path

from grounded_research.config import get_fallback_models, get_model
from grounded_research.models import DecompositionValidation
from grounded_research.runtime_policy import get_request_timeout
from grounded_research.tyler_v1_adapters import normalize_tyler_decomposition_ids
from grounded_research.tyler_v1_models import DecompositionResult

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


async def decompose_question_tyler_v1(
    question: str,
    trace_id: str,
    max_budget: float = 0.5,
) -> DecompositionResult:
    """Run Tyler's literal Stage 1 decomposition contract.

    This is the migration entrypoint for literal-parity work. It does not yet
    replace the shipped runtime surface, but it produces Tyler-native
    `DecompositionResult` artifacts for the staged refactor.
    """
    from llm_client import acall_llm_structured, render_prompt

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "tyler_v1_decompose.yaml"),
        original_query=question,
        response_schema_json=DecompositionResult.model_json_schema(),
    )

    model = get_model("decomposition")
    result, _meta = await acall_llm_structured(
        model,
        messages,
        response_model=DecompositionResult,
        task="question_decomposition_tyler_v1",
        trace_id=f"{trace_id}/decompose_tyler_v1",
        timeout=get_request_timeout("decomposition"),
        max_budget=max_budget,
        fallback_models=get_fallback_models("decomposition"),
    )
    return normalize_tyler_decomposition_ids(result)


async def validate_decomposition(
    question: str,
    decomposition: DecompositionResult,
    trace_id: str,
    max_budget: float = 0.3,
) -> DecompositionValidation:
    """Validate a Tyler Stage 1 decomposition for coverage, bias, and granularity."""
    from llm_client import acall_llm_structured, render_prompt

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "validate_decomposition.yaml"),
        question=question,
        decomposition={
            "core_question": decomposition.core_question,
            "sub_questions": [
                {
                    "type": sub_question.type,
                    "text": sub_question.question,
                    "falsification_target": (
                        decomposition.research_plan.falsification_targets[idx]
                        if idx < len(decomposition.research_plan.falsification_targets)
                        else "Contradictory high-quality evidence"
                    ),
                }
                for idx, sub_question in enumerate(decomposition.sub_questions)
            ],
            "optimization_axes": decomposition.optimization_axes,
        },
    )

    model = get_model("decomposition")
    result, _meta = await acall_llm_structured(
        model,
        messages,
        response_model=DecompositionValidation,
        task="decomposition_validation",
        trace_id=f"{trace_id}/validate_decomp",
        timeout=get_request_timeout("decomposition"),
        max_budget=max_budget,
        fallback_models=get_fallback_models("decomposition"),
    )

    return result


async def decompose_with_validation_tyler_v1(
    question: str,
    trace_id: str,
    max_budget: float = 0.5,
    time_sensitivity: str = "mixed",
) -> tuple[DecompositionResult, DecompositionValidation | None]:
    """Run Tyler-native Stage 1, then validate the Tyler artifact directly.

    The live Stage 1 output is Tyler's `DecompositionResult`. Validation should
    operate on that canonical artifact directly rather than on a projected
    current-shape decomposition.
    """
    import logging
    del time_sensitivity

    logger = logging.getLogger(__name__)

    tyler_result = await decompose_question_tyler_v1(
        question=question,
        trace_id=trace_id,
        max_budget=max_budget * 0.4,
    )
    validation = await validate_decomposition(
        question, tyler_result, trace_id, max_budget * 0.2,
    )

    if validation.verdict == "revise" and validation.revision_guidance:
        logger.info("Decomposition revision requested: %s", validation.revision_guidance)
        revised_question = f"{question}\n\n[Revision guidance: {validation.revision_guidance}]"
        tyler_result = await decompose_question_tyler_v1(
            question=revised_question,
            trace_id=f"{trace_id}/retry",
            max_budget=max_budget * 0.4,
        )
        validation = await validate_decomposition(
            question, tyler_result, f"{trace_id}/retry", max_budget * 0.2,
        )
        if validation.verdict == "revise":
            logger.warning("Decomposition still needs revision after retry, proceeding anyway")

    return tyler_result, validation
