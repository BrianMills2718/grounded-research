"""Adapters between the shipped runtime models and Tyler V1 literal contracts.

These adapters support the staged literal-parity migration. They make it
possible to generate Tyler-native artifacts without forcing the whole runtime
to switch contracts in one unsafe step.
"""

from __future__ import annotations

from grounded_research.models import QuestionDecomposition, SubQuestion, _make_id
from grounded_research.tyler_v1_models import DecompositionResult


def normalize_tyler_decomposition_ids(result: DecompositionResult) -> DecompositionResult:
    """Normalize Tyler Stage 1 IDs after LLM generation.

    The LLM can override schema descriptions and emit arbitrary IDs. Tyler's
    Stage 1 contract expects `Q-{n}` IDs. This function rewrites malformed IDs
    into deterministic sequential `Q-{n}` values.
    """
    for idx, sub_question in enumerate(result.sub_questions, start=1):
        if not sub_question.id.startswith("Q-"):
            sub_question.id = f"Q-{idx}"
    return result


def tyler_decomposition_to_current(result: DecompositionResult) -> QuestionDecomposition:
    """Convert Tyler's Stage 1 artifact into the current runtime decomposition.

    This keeps the runtime operational while Stage 1 begins migrating toward the
    literal Tyler contract.
    """
    type_map = {
        "empirical": "factual",
        "interpretive": "evaluative",
        "preference": "evaluative",
    }
    return QuestionDecomposition(
        core_question=result.core_question,
        sub_questions=[
            SubQuestion(
                id=_make_id("SQ-"),
                text=sq.question,
                type=type_map.get(sq.type, "scope"),
                falsification_target=(
                    result.research_plan.falsification_targets[idx]
                    if idx < len(result.research_plan.falsification_targets)
                    else "N/A"
                ),
            )
            for idx, sq in enumerate(result.sub_questions)
        ],
        optimization_axes=result.optimization_axes,
        research_plan=(
            "Verify: "
            + "; ".join(result.research_plan.what_to_verify)
            + ". Critical sources: "
            + ", ".join(result.research_plan.critical_source_types)
        ),
        ambiguous_terms=[],
    )
