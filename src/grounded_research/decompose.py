"""Question decomposition: break a research question into typed sub-questions.

Phase A of the v2 pipeline. Runs before evidence collection to focus
search queries per sub-question and give analysts structured context.
See ADR-0006 for design decisions.
"""

from __future__ import annotations

from pathlib import Path

from grounded_research.config import get_fallback_models, get_model
from grounded_research.models import QuestionDecomposition

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
        max_budget=max_budget,
        fallback_models=get_fallback_models("decomposition"),
    )

    return result
