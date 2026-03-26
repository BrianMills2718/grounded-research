"""Question decomposition: break a research question into typed sub-questions.

Phase A of the v2 pipeline. Runs before evidence collection to focus
search queries per sub-question and give analysts structured context.
See ADR-0006 for design decisions.
"""

from __future__ import annotations

from pathlib import Path

from grounded_research.config import get_fallback_models, get_model
from grounded_research.models import DecompositionValidation, QuestionDecomposition, _make_id
from grounded_research.runtime_policy import get_request_timeout

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


async def decompose_question(
    question: str,
    trace_id: str,
    max_budget: float = 0.5,
    time_sensitivity: str = "mixed",
) -> QuestionDecomposition:
    """Decompose a research question into typed sub-questions.

    Returns a QuestionDecomposition with core question, sub-questions,
    optimization axes, and a research plan. Uses structured output to
    guarantee schema compliance.
    """
    from llm_client import acall_llm_structured, render_prompt

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "decompose.yaml"),
        question=question,
        time_sensitivity=time_sensitivity,
    )

    model = get_model("decomposition")
    result, _meta = await acall_llm_structured(
        model,
        messages,
        response_model=QuestionDecomposition,
        task="question_decomposition",
        trace_id=f"{trace_id}/decompose",
        timeout=get_request_timeout("decomposition"),
        max_budget=max_budget,
        fallback_models=get_fallback_models("decomposition"),
    )

    # Assign proper SQ- IDs — the LLM may have overridden the default_factory
    # with arbitrary values like "1", "2", etc.
    for sq in result.sub_questions:
        if not sq.id.startswith("SQ-"):
            sq.id = _make_id("SQ-")

    return result


async def validate_decomposition(
    question: str,
    decomposition: QuestionDecomposition,
    trace_id: str,
    max_budget: float = 0.3,
) -> DecompositionValidation:
    """Validate a question decomposition for coverage, bias, and granularity.

    Returns a DecompositionValidation with verdict (proceed/revise).
    """
    from llm_client import acall_llm_structured, render_prompt

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "validate_decomposition.yaml"),
        question=question,
        decomposition=decomposition.model_dump(),
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


async def decompose_with_validation(
    question: str,
    trace_id: str,
    max_budget: float = 0.5,
    time_sensitivity: str = "mixed",
) -> tuple[QuestionDecomposition, DecompositionValidation | None]:
    """Decompose a question and validate the result. Retry once if verdict is 'revise'.

    Returns (decomposition, validation). Validation is None if skipped.
    """
    import logging
    logger = logging.getLogger(__name__)

    decomp = await decompose_question(question, trace_id, max_budget * 0.4, time_sensitivity)

    validation = await validate_decomposition(
        question, decomp, trace_id, max_budget * 0.2,
    )

    if validation.verdict == "revise" and validation.revision_guidance:
        logger.info("Decomposition revision requested: %s", validation.revision_guidance)
        # Re-decompose with guidance appended
        revised_question = f"{question}\n\n[Revision guidance: {validation.revision_guidance}]"
        decomp = await decompose_question(revised_question, f"{trace_id}/retry", max_budget * 0.4, time_sensitivity)

        # Validate again (but don't retry a second time)
        validation = await validate_decomposition(
            question, decomp, f"{trace_id}/retry", max_budget * 0.2,
        )
        if validation.verdict == "revise":
            logger.warning("Decomposition still needs revision after retry, proceeding anyway")

    return decomp, validation
