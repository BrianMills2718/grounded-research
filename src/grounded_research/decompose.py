"""Question decomposition: break a research question into typed sub-questions.

Phase A of the v2 pipeline. Runs before evidence collection to focus
search queries per sub-question and give analysts structured context.
See ADR-0006 for design decisions.
"""

from __future__ import annotations

from pathlib import Path

from grounded_research.config import get_fallback_models, get_model
from grounded_research.tyler_v1_adapters import normalize_tyler_decomposition_ids
from grounded_research.tyler_v1_models import DecompositionResult

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


async def decompose_question_tyler_v1(
    question: str,
    trace_id: str,
    max_budget: float = 0.5,
) -> DecompositionResult:
    """Run Tyler's literal Stage 1 decomposition contract.

    Tyler V1 removed the separate decomposition-validation stage. The Stage 1
    prompt's self-check is the only live mitigation before the pipeline moves
    into retrieval.
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
        max_budget=max_budget,
        fallback_models=get_fallback_models("decomposition"),
    )
    return normalize_tyler_decomposition_ids(result)
