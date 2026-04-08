"""Claim canonicalization for the Tyler-native adjudication pipeline.

The live runtime consumes Tyler Stage 3 analysis objects and produces the
canonical Tyler Stage 4 artifact. Deleted compatibility dedup/dispute helpers
are intentionally excluded from `main`.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import random

from grounded_research.config import (
    get_fallback_models,
    get_model,
    get_tyler_literal_parity_config,
)
from grounded_research.models import EvidenceBundle
from grounded_research.tyler_v1_adapters import normalize_tyler_claim_extraction_result
from grounded_research.tyler_v1_models import (
    AnalysisObject,
    ClaimExtractionResult as TylerClaimExtractionResult,
    DecompositionResult as TylerDecompositionResult,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Tyler Stage 4 runtime path
# ---------------------------------------------------------------------------


def _tyler_stage4_assertion_count(stage_3_results: list["AnalysisObject"]) -> int:
    """Count extractable Stage 3 assertions before Stage 4 runs.

    A schema-valid empty Stage 4 result is only acceptable when the upstream
    Tyler analyses are themselves empty. When analysts produced claims or
    assumptions, Stage 4 must not silently collapse to an empty ledger.
    """
    return sum(len(result.claims) + len(result.assumptions) for result in stage_3_results)


def _summarize_stage4_exception(exc: Exception) -> str:
    """Summarize Stage 4 schema/runtime failures for a corrective retry prompt."""
    lines = [line.strip() for line in str(exc).splitlines() if line.strip()]
    return " | ".join(lines[:8])[:1200]


def _randomize_stage4_analysis_order(
    stage_3_results: list["AnalysisObject"],
    *,
    rng: random.Random | random.SystemRandom | None = None,
) -> list["AnalysisObject"]:
    """Shuffle Stage 3 analyst presentation order for Tyler Stage 4.

    Tyler requires the analyst order to be randomized before each Stage 4 call
    to reduce primacy bias. This helper returns a reordered copy so caller-owned
    Stage 3 artifacts stay stable for tracing and later phases.
    """
    shuffled = list(stage_3_results)
    if len(shuffled) > 1:
        shuffler = rng or random.SystemRandom()
        shuffler.shuffle(shuffled)
    return shuffled


def _render_stage4_messages(
    *,
    original_query: str,
    tyler_stage1: TylerDecompositionResult,
    stage_3_results: list["AnalysisObject"],
) -> tuple[list[dict[str, object]], list["AnalysisObject"]]:
    """Build Stage 4 prompt messages from a freshly randomized analyst order."""
    from llm_client import render_prompt

    randomized_stage3 = _randomize_stage4_analysis_order(stage_3_results)
    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "tyler_v1_stage4.yaml"),
        original_query=original_query,
        stage_1=tyler_stage1.model_dump(mode="json"),
        stage_3_results=[analysis.model_dump(mode="json") for analysis in randomized_stage3],
        response_schema_json=TylerClaimExtractionResult.model_json_schema(),
    )
    return messages, randomized_stage3


async def _get_tyler_stage1_result(
    *,
    original_query: str,
    trace_id: str,
    max_budget: float,
) -> TylerDecompositionResult:
    """Produce a Tyler-native Stage 1 artifact for Stage 4 prompt rendering.

    Canonical Stage 4 should depend on Tyler Stage 1 directly. If the persisted
    Tyler artifact is missing, regenerate it from the original question rather
    than reconstructing a deleted compatibility decomposition surface.
    """

    from grounded_research.decompose import decompose_question_tyler_v1

    return await decompose_question_tyler_v1(
        question=original_query,
        trace_id=trace_id,
        max_budget=max_budget,
    )


async def canonicalize_tyler_v1(
    bundle: EvidenceBundle,
    *,
    tyler_stage_1_result: TylerDecompositionResult | None = None,
    tyler_stage_3_results: list["AnalysisObject"],
    tyler_stage_3_alias_mapping: dict[str, str],
    trace_id: str,
    max_budget: float = 1.0,
) -> TylerClaimExtractionResult:
    """Run Tyler's literal Stage 4 contract and return only the canonical artifact."""
    from llm_client import acall_llm_structured

    original_query = bundle.question.text if bundle.question else ""
    tyler_stage1 = tyler_stage_1_result or await _get_tyler_stage1_result(
        original_query=original_query,
        trace_id=f"{trace_id}/stage1_adapter",
        max_budget=max_budget * 0.15,
    )
    tyler_stage3_results = list(tyler_stage_3_results)
    if len(tyler_stage3_results) < 2:
        raise ValueError("Tyler Stage 4 requires at least 2 Tyler Stage 3 analysis objects.")
    alias_mapping = dict(tyler_stage_3_alias_mapping)
    stage4_input_assertions = _tyler_stage4_assertion_count(tyler_stage3_results)
    parity_policy = get_tyler_literal_parity_config()

    async def _run_stage4_retry(issue_summary: str) -> TylerClaimExtractionResult:
        retry_messages, _randomized_retry_stage3 = _render_stage4_messages(
            original_query=original_query,
            tyler_stage1=tyler_stage1,
            stage_3_results=tyler_stage3_results,
        )
        retry_messages.append(
            {
                "role": "user",
                "content": (
                    "Correction for Tyler Stage 4: the previous response was not acceptable. "
                    f"Issue: {issue_summary} "
                    "Retry now. Keep the exact same schema, but place only assumptions in "
                    "`assumption_set`, place all disputes in `dispute_queue`, populate "
                    "`statistics.claims_per_model`, and do not return an empty claim ledger "
                    "when the analyses contain extractable assertions."
                ),
            }
        )
        retry_model = str(parity_policy.get("stage4_retry_model") or get_model("claim_extraction"))
        retry_fallback_models = parity_policy.get("stage4_retry_fallback_models")
        retry_result, _retry_meta = await acall_llm_structured(
            retry_model,
            retry_messages,
            response_model=TylerClaimExtractionResult,
            task="claim_extraction_tyler_v1_retry",
            trace_id=f"{trace_id}/claim_extraction_tyler_v1_retry",
            max_budget=max_budget,
            fallback_models=retry_fallback_models if retry_fallback_models else get_fallback_models("claim_extraction"),
        )
        return retry_result

    messages, _randomized_stage3 = _render_stage4_messages(
        original_query=original_query,
        tyler_stage1=tyler_stage1,
        stage_3_results=tyler_stage3_results,
    )
    try:
        result, _meta = await acall_llm_structured(
            get_model("claim_extraction"),
            messages,
            response_model=TylerClaimExtractionResult,
            task="claim_extraction_tyler_v1",
            trace_id=f"{trace_id}/claim_extraction_tyler_v1",
            max_budget=max_budget,
            fallback_models=get_fallback_models("claim_extraction"),
        )
    except Exception as exc:
        if not bool(parity_policy.get("stage4_retry_on_empty_claims", True)) or stage4_input_assertions <= 0:
            raise
        result = await _run_stage4_retry(
            f"schema or validation failure from the primary Stage 4 call: {_summarize_stage4_exception(exc)}"
        )

    normalized = normalize_tyler_claim_extraction_result(
        result,
        valid_source_ids={source.id for source in bundle.sources},
        allowed_model_aliases=set(alias_mapping.values()),
    )
    should_retry_empty_stage4 = (
        bool(parity_policy.get("stage4_retry_on_empty_claims", True))
        and stage4_input_assertions > 0
        and not normalized.claim_ledger
        and not normalized.assumption_set
    )
    if should_retry_empty_stage4:
        retry_result = await _run_stage4_retry(
            "the previous Stage 4 result extracted zero claims and zero assumptions "
            f"from analyses containing {stage4_input_assertions} upstream claims/assumptions."
        )
        normalized = normalize_tyler_claim_extraction_result(
            retry_result,
            valid_source_ids={source.id for source in bundle.sources},
            allowed_model_aliases=set(alias_mapping.values()),
        )
        if not normalized.claim_ledger and not normalized.assumption_set:
            raise ValueError(
                "Tyler Stage 4 returned an empty claim ledger and assumption set "
                f"after retry despite {stage4_input_assertions} upstream assertions."
            )
    return normalized
