"""Canonical Tyler-native export and downstream handoff.

This module owns the final export boundary for the live runtime:

1. Generate Tyler Stage 6 `SynthesisReport`
2. Render `report.md` directly from Stage 6
3. Render `summary.md` directly from Stage 6
4. Emit `handoff.json` as a Tyler-native downstream artifact

Legacy `FinalReport` and legacy handoff surfaces are intentionally excluded from
the live export path so the repo keeps one canonical output contract.
"""

from __future__ import annotations

from collections import Counter
import json
import logging
from pathlib import Path
import re
import sqlite3
import uuid

from grounded_research.config import (
    get_fallback_models,
    get_model,
    get_tyler_literal_parity_config,
    load_config,
)
from grounded_research.models import (
    EvidenceBundle,
    PipelineState,
    TylerDownstreamHandoff,
)
from grounded_research.tyler_v1_adapters import render_tyler_synthesis_markdown
from grounded_research.tyler_v1_models import (
    PipelineError as TylerPipelineError,
    PipelineState as TylerPipelineState,
    SynthesisReport,
    VerificationResult,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LOG = logging.getLogger(__name__)
_CLAIM_ID_RE = re.compile(r"\bC-\d+\b")
_STAGE_PREFIX_RE = re.compile(r"^(Stage \d+)\b")
_CONDITIONAL_MARKER_RE = re.compile(r"\b(if|unless|when)\b", re.IGNORECASE)


def _truncate_text(text: str, max_chars: int) -> str:
    """Trim verbose synthesis context while preserving readable intent."""
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return text[: max_chars - 3].rstrip() + "..."


def _extract_stage_prefix(stage_name: str) -> str | None:
    """Normalize `Stage N ...` labels to the comparable `Stage N` prefix."""
    match = _STAGE_PREFIX_RE.match(stage_name.strip())
    return match.group(1) if match else None


def _expected_process_summary_prefixes(
    all_stage_summaries: list[dict[str, object]],
) -> list[str]:
    """Derive the executed stage-prefix set Tyler expects in `process_summary`."""
    expected: list[str] = []
    for summary in all_stage_summaries:
        prefix = _extract_stage_prefix(str(summary.get("stage_name", "")))
        if prefix and prefix not in expected:
            expected.append(prefix)
    if "Stage 6" not in expected:
        expected.append("Stage 6")
    return expected


def _infer_tyler_current_stage(state: PipelineState) -> int:
    """Infer Tyler's numeric current-stage field from the populated runtime state."""
    if state.tyler_stage_6_result is not None:
        return 6
    if state.tyler_stage_5_result is not None:
        return 5
    if state.tyler_stage_4_result is not None:
        return 4
    if state.tyler_stage_3_results or state.tyler_stage_3_alias_mapping or state.stage3_attempts:
        return 3
    if state.tyler_stage_2_result is not None or state.evidence_bundle is not None:
        return 2
    return 1


def _warning_to_tyler_pipeline_error(
    warning_code: str,
    *,
    stage: int,
    message: str,
) -> TylerPipelineError:
    """Convert a failed-run warning into Tyler's `PipelineError` surface."""
    text = f"{warning_code} {message}".lower()
    if "timeout" in text:
        error_type = "timeout"
    elif "budget" in text:
        error_type = "budget_exceeded"
    elif "json" in text:
        error_type = "invalid_json"
    elif any(token in text for token in ("auth", "quota", "rate", "api")):
        error_type = "api_failure"
    else:
        error_type = "validation_error"
    return TylerPipelineError(
        stage=stage,
        error_type=error_type,
        message=message,
        recoverable=False,
        action_taken="aborted",
    )


def _load_total_cost_usd(
    *,
    observability_db_path: Path | None,
    trace_id_root: str | None,
    phase_traces: list,
) -> float | None:
    """Best-effort total-cost rollup for Tyler's trace contract."""
    fallback_total = sum(float(getattr(trace, "llm_cost_usd", 0.0)) for trace in phase_traces)
    if observability_db_path is None or trace_id_root is None or not observability_db_path.exists():
        return fallback_total or None

    try:
        conn = sqlite3.connect(str(observability_db_path))
        try:
            total = 0.0
            for table in ("llm_calls", "tool_calls"):
                table_exists = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                ).fetchone()
                if not table_exists:
                    continue
                value = conn.execute(
                    f"SELECT COALESCE(SUM(cost), 0.0) FROM {table} "
                    "WHERE trace_id = ? OR trace_id LIKE ?",
                    (trace_id_root, f"{trace_id_root}/%"),
                ).fetchone()
                total += float(value[0] or 0.0)
            return total or fallback_total or None
        finally:
            conn.close()
    except sqlite3.Error:
        return fallback_total or None


def build_tyler_pipeline_state(
    state: PipelineState,
    *,
    observability_db_path: Path | None = None,
    trace_id_root: str | None = None,
) -> TylerPipelineState:
    """Project the repo-local runtime state onto Tyler's canonical trace contract."""
    query_id = state.run_id
    if len(query_id) != 36:
        query_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"grounded-research:{state.run_id}"))

    current_stage = _infer_tyler_current_stage(state)
    stage_6_user_input = "\n".join(state.user_guidance_notes).strip() or None
    error_rows = [
        _warning_to_tyler_pipeline_error(
            warning.code,
            stage=current_stage,
            message=warning.message,
        )
        for warning in state.warnings
        if warning.phase == "failed" or warning.code == "pipeline_error"
    ]

    return TylerPipelineState(
        query_id=query_id,
        original_query=(
            state.question.text
            if state.question is not None
            else state.evidence_bundle.question.text
            if state.evidence_bundle is not None
            else ""
        ),
        started_at=state.started_at.isoformat(),
        current_stage=current_stage,
        stage_1_result=state.tyler_stage_1_result,
        stage_2_result=state.tyler_stage_2_result,
        stage_3_alias_mapping=state.tyler_stage_3_alias_mapping or None,
        stage_3_results=state.tyler_stage_3_results or None,
        stage_4_result=state.tyler_stage_4_result,
        stage_5_result=state.tyler_stage_5_result,
        stage_5_skipped=state.tyler_stage_5_result is None,
        stage_6_user_input=stage_6_user_input,
        stage_6_result=state.tyler_stage_6_result,
        completed_at=state.completed_at.isoformat() if state.completed_at is not None else None,
        errors=error_rows,
        total_cost_usd=_load_total_cost_usd(
            observability_db_path=observability_db_path,
            trace_id_root=trace_id_root,
            phase_traces=state.phase_traces,
        ),
    )


def write_tyler_trace(
    state: PipelineState,
    output_dir: Path,
    *,
    observability_db_path: Path | None = None,
    trace_id_root: str | None = None,
) -> Path:
    """Write Tyler's canonical `PipelineState` trace artifact to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = output_dir / "trace.json"
    trace = build_tyler_pipeline_state(
        state,
        observability_db_path=observability_db_path,
        trace_id_root=trace_id_root,
    )
    trace_path.write_text(trace.model_dump_json(indent=2))
    return trace_path


def _build_stage6_top_sources(
    *,
    bundle: EvidenceBundle,
    verification_result: VerificationResult,
    top_sources_cap: int,
    non_dispute_summary_chars: int,
) -> list[dict[str, object]]:
    """Assemble Tyler Stage 6 source context from both Stage 2 and Stage 5.

    Tyler expects synthesis to see sources that contributed to dispute
    resolution, including the targeted verification sources discovered in
    Stage 5. This helper merges both inventories into one prompt-facing source
    summary surface.
    """
    investigated_dispute_ids = {
        assessment.dispute_id for assessment in verification_result.disputes_investigated
    }
    claim_ids_by_source: dict[str, list[str]] = {}
    for claim in verification_result.updated_claim_ledger:
        for source_id in claim.source_references:
            claim_ids_by_source.setdefault(source_id, []).append(claim.id)

    disputes_by_source: dict[str, list[str]] = {}
    for dispute in verification_result.updated_dispute_queue:
        if dispute.id not in investigated_dispute_ids:
            continue
        for claim_id in dispute.claims_involved:
            for claim in verification_result.updated_claim_ledger:
                if claim.id != claim_id:
                    continue
                for source_id in claim.source_references:
                    disputes_by_source.setdefault(source_id, []).append(dispute.id)

    top_sources: list[dict[str, object]] = []
    seen_ids: set[str] = set()

    for source in bundle.sources:
        contribution_claims = list(dict.fromkeys(claim_ids_by_source.get(source.id, [])))
        resolved_disputes = list(dict.fromkeys(disputes_by_source.get(source.id, [])))
        if not contribution_claims and not resolved_disputes:
            continue
        top_sources.append(
            {
                "id": source.id,
                "title": source.title,
                "quality_score": {
                    "authoritative": 1.0,
                    "reliable": 0.7,
                    "unknown": 0.5,
                    "unreliable": 0.3,
                }.get(source.quality_tier, 0.5),
                "source_type": source.source_type,
                "contribution_summary": (
                    f"Supports claims {', '.join(contribution_claims[:4])}"
                    if contribution_claims
                    else "Contributed to dispute resolution."
                ),
                "conflicts_resolved": resolved_disputes,
            }
        )
        seen_ids.add(source.id)

    for source in verification_result.additional_sources:
        if source.source_id in seen_ids:
            continue
        resolved_disputes = [source.retrieved_for_dispute] if source.retrieved_for_dispute in investigated_dispute_ids else []
        contribution_summary = "; ".join(source.key_findings[:2]) or "Retrieved during Stage 5 targeted verification."
        if not resolved_disputes:
            contribution_summary = _truncate_text(contribution_summary, non_dispute_summary_chars)
        top_sources.append(
            {
                "id": source.source_id,
                "title": source.title,
                "quality_score": source.quality_score,
                "source_type": "verification_additional",
                "contribution_summary": contribution_summary,
                "conflicts_resolved": resolved_disputes,
            }
        )
        seen_ids.add(source.source_id)

    return top_sources[:top_sources_cap]


def _build_stage6_user_response_map(
    *,
    dispute_queue: list[dict[str, object]],
    user_clarifications: str,
) -> dict[str, str]:
    """Map Stage 6 user steering text onto the Tyler prompt variable surface."""
    cleaned = user_clarifications.strip()
    if not cleaned:
        return {}
    return {
        str(dispute["id"]): cleaned
        for dispute in dispute_queue
        if str(dispute.get("status", "")) == "deferred_to_user"
    }


def _compact_stage6_prompt_inputs(
    *,
    original_query: str,
    claim_ledger: list[dict[str, object]],
    decision_critical_claim_ids: set[str],
    user_response_for_dispute: dict[str, str],
    assumption_set: list[dict[str, object]],
    dispute_queue: list[dict[str, object]],
    top_sources: list[dict[str, object]],
    evidence_gaps: list[str],
    all_stage_summaries: list[dict[str, object]],
    char_limit: int,
    noncritical_claim_chars: int,
    non_dispute_summary_chars: int,
) -> dict[str, object]:
    """Apply Tyler's Stage 6 char-budget compaction policy when needed."""
    payload: dict[str, object] = {
        "original_query": original_query,
        "claim_ledger": claim_ledger,
        "decision_critical_claim_ids": decision_critical_claim_ids,
        "user_response_for_dispute": user_response_for_dispute,
        "assumption_set": assumption_set,
        "dispute_queue": dispute_queue,
        "top_sources": top_sources,
        "evidence_gaps": evidence_gaps,
        "all_stage_summaries": all_stage_summaries,
    }
    if len(json.dumps(payload, default=str)) <= char_limit:
        return payload

    compacted_claim_ledger: list[dict[str, object]] = []
    for claim in claim_ledger:
        if str(claim["id"]) in decision_critical_claim_ids:
            compacted_claim_ledger.append(claim)
            continue
        compacted_claim_ledger.append(
            {
                "id": claim["id"],
                "statement": _truncate_text(str(claim["statement"]), noncritical_claim_chars),
                "status": claim["status"],
            }
        )
    compacted_top_sources = [
        {
            **source,
            "contribution_summary": (
                source["contribution_summary"]
                if source.get("conflicts_resolved")
                else _truncate_text(str(source["contribution_summary"]), non_dispute_summary_chars)
            ),
        }
        for source in top_sources
    ]
    compacted_stage_summaries = [
        {
            "stage_name": summary["stage_name"],
            "goal": _truncate_text(str(summary["goal"]), 120),
            "key_findings": [_truncate_text(str(item), 120) for item in list(summary["key_findings"])[:3]],
            "decisions_made": [_truncate_text(str(item), 120) for item in list(summary["decisions_made"])[:2]],
            "outcome": _truncate_text(str(summary["outcome"]), 160),
            "reasoning": _truncate_text(str(summary["reasoning"]), 200),
        }
        for summary in all_stage_summaries
    ]
    return {
        **payload,
        "claim_ledger": compacted_claim_ledger,
        "top_sources": compacted_top_sources,
        "all_stage_summaries": compacted_stage_summaries,
    }


def _select_stage6_synthesis_model(state: PipelineState) -> tuple[str, list[str] | None]:
    """Choose a non-dominant synthesis model for Tyler Stage 6 when possible."""
    config = load_config()
    model_counts: Counter[str] = Counter()
    for task in ("decomposition", "evidence_extraction", "claim_extraction", "arbitration"):
        model_counts[get_model(task)] += 1
    if state.stage3_attempts:
        for attempt in state.stage3_attempts:
            if attempt.succeeded:
                model_counts[attempt.model] += 1
    else:
        for model in config.get("analyst_models", []):
            model_counts[str(model)] += 1

    dominant_count = max(model_counts.values(), default=0)
    dominant_models = {model for model, count in model_counts.items() if count == dominant_count}
    synthesis_model = get_model("synthesis")
    fallback_models = list(get_fallback_models("synthesis") or [])
    if synthesis_model not in dominant_models:
        return synthesis_model, fallback_models or None

    for candidate in fallback_models:
        if candidate not in dominant_models:
            remaining = [model for model in fallback_models if model != candidate and model not in dominant_models]
            return candidate, remaining or None

    raise ValueError(
        "Tyler Stage 6 requires a non-dominant synthesis model, but the configured "
        "primary/fallback synthesis models are all dominant earlier-stage models."
    )


def validate_tyler_grounding(
    report: SynthesisReport,
    *,
    verification_result: VerificationResult,
    bundle: EvidenceBundle,
) -> list[str]:
    """Validate the canonical Tyler Stage 6 artifact against Stage 5 and sources."""
    errors: list[str] = []
    claim_map = {claim.id: claim for claim in verification_result.updated_claim_ledger}
    source_ids = {source.id for source in bundle.sources}
    source_ids.update(source.source_id for source in verification_result.additional_sources)
    cited_claim_ids = set(_CLAIM_ID_RE.findall(report.executive_recommendation))

    if not cited_claim_ids:
        errors.append(
            "Executive recommendation cites no claim IDs from the Tyler claim ledger."
        )
    else:
        unknown_cited_claim_ids = sorted(cited_claim_ids - set(claim_map))
        if unknown_cited_claim_ids:
            errors.append(
                "Executive recommendation cites unknown claim IDs: "
                + ", ".join(unknown_cited_claim_ids)
            )

    for excerpt in report.claim_ledger_excerpt:
        claim = claim_map.get(excerpt.claim_id)
        if claim is None:
            errors.append(f"Claim excerpt {excerpt.claim_id} not found in Tyler Stage 5 ledger")
            continue
        if not claim.source_references:
            errors.append(
                f"Claim excerpt {excerpt.claim_id} has no source references in Tyler Stage 5 ledger"
            )
            continue
        missing_refs = [source_id for source_id in claim.source_references if source_id not in source_ids]
        if missing_refs:
            errors.append(
                f"Claim excerpt {excerpt.claim_id} references unknown sources: {', '.join(missing_refs)}"
            )

    evidence_trail_ids = {source.source_id for source in report.evidence_trail}
    unknown_trail_ids = sorted(evidence_trail_ids - source_ids)
    for source_id in unknown_trail_ids:
        errors.append(f"Evidence trail source {source_id} not found in Stage 2/5 source inventory")

    unresolved_dispute_ids = {
        dispute.id
        for dispute in verification_result.updated_dispute_queue
        if dispute.status is not None and dispute.status.value == "unresolved"
    }
    mentioned_dispute_ids = {entry.dispute_id for entry in report.disagreement_map}
    missing_disputes = sorted(unresolved_dispute_ids - mentioned_dispute_ids)
    for dispute_id in missing_disputes:
        errors.append(f"Unresolved Tyler dispute {dispute_id} not mentioned in disagreement_map")

    return errors


def _validate_tyler_synthesis_report(
    report: SynthesisReport,
    *,
    unresolved_dispute_ids: set[str],
    verification_result: VerificationResult,
    bundle: EvidenceBundle,
    expected_process_summary_prefixes: list[str],
    min_tradeoffs: int,
    min_preserved_alternatives: int,
    min_conditions_of_validity: int,
    max_conditional_markers: int,
) -> list[str]:
    """Return repair feedback for underfilled Tyler Stage 6 outputs.

    Includes zombie check per Tyler V1 spec: preserved alternatives must
    not reference refuted claims.
    """
    errors = validate_tyler_grounding(
        report,
        verification_result=verification_result,
        bundle=bundle,
    )
    if len(report.decision_relevant_tradeoffs) < min_tradeoffs:
        errors.append(
            "decision_relevant_tradeoffs is underfilled. Add concrete decision tradeoffs tied to the recommendation and evidence."
        )
    if len(report.preserved_alternatives) < min_preserved_alternatives:
        errors.append(
            "preserved_alternatives is underfilled. Preserve at least one viable alternative when different conditions would rationally change the recommendation."
        )
    if len(report.conditions_of_validity) < min_conditions_of_validity:
        errors.append(
            "conditions_of_validity is underfilled. Include at least one explicit condition that would flip the recommendation."
        )
    disagreement_ids = {entry.dispute_id for entry in report.disagreement_map}
    missing_unresolved = sorted(unresolved_dispute_ids - disagreement_ids)
    if missing_unresolved:
        errors.append(
            "disagreement_map is missing unresolved disputes: " + ", ".join(missing_unresolved)
        )

    claim_ledger = verification_result.updated_claim_ledger
    claim_ids = {claim.id for claim in claim_ledger}
    refuted_ids = {
        claim.id
        for claim in claim_ledger
        if str(getattr(claim.status, "value", claim.status)) == "refuted"
    }
    for alt in report.preserved_alternatives:
        invalid_refs = [cid for cid in alt.supporting_claims if cid not in claim_ids]
        if invalid_refs:
            errors.append(
                f"preserved_alternatives contains unknown supporting_claims IDs: {', '.join(invalid_refs)}"
            )
        zombie_refs = [cid for cid in alt.supporting_claims if cid in refuted_ids]
        if zombie_refs:
            errors.append(
                f"ZOMBIE: preserved alternative '{alt.alternative[:60]}...' cites refuted "
                f"claim(s): {', '.join(zombie_refs)}. Remove refuted alternatives or update claims."
            )

    reported_prefixes = {
        prefix
        for prefix in (
            _extract_stage_prefix(summary.stage_name)
            for summary in report.process_summary
        )
        if prefix is not None
    }
    missing_process_summaries = [
        prefix
        for prefix in expected_process_summary_prefixes
        if prefix not in reported_prefixes
    ]
    if missing_process_summaries:
        errors.append(
            "process_summary is missing executed stages: "
            + ", ".join(missing_process_summaries)
        )

    conditional_markers = len(_CONDITIONAL_MARKER_RE.findall(report.executive_recommendation))
    if conditional_markers > max_conditional_markers:
        errors.append(
            "executive_recommendation exceeds Tyler's conditional-nesting limit. "
            f"Found {conditional_markers} conditional markers; max allowed is {max_conditional_markers}."
        )

    return errors


def build_tyler_downstream_handoff(state: PipelineState) -> TylerDownstreamHandoff:
    """Build the canonical Tyler-native downstream artifact."""
    assert state.question is not None
    assert state.tyler_stage_2_result is not None
    assert state.tyler_stage_5_result is not None
    assert state.tyler_stage_6_result is not None
    return TylerDownstreamHandoff(
        question=state.question,
        stage_2_evidence_package=state.tyler_stage_2_result,
        stage_5_verification_result=state.tyler_stage_5_result,
        stage_6_synthesis_report=state.tyler_stage_6_result,
    )


async def generate_tyler_synthesis_report(
    state: PipelineState,
    *,
    trace_id: str,
    max_budget: float = 1.0,
) -> SynthesisReport:
    """Run Tyler's literal Stage 6 synthesis contract."""
    from llm_client import acall_llm_structured, render_prompt

    assert state.tyler_stage_4_result is not None
    assert state.tyler_stage_5_result is not None
    assert state.evidence_bundle is not None
    assert state.question is not None
    parity_policy = get_tyler_literal_parity_config()

    if state.tyler_stage_1_result is not None:
        tyler_stage1 = state.tyler_stage_1_result
    else:
        from grounded_research.decompose import decompose_question_tyler_v1

        tyler_stage1 = await decompose_question_tyler_v1(
            question=state.question.text,
            trace_id=f"{trace_id}/stage1_for_synthesis",
            max_budget=max_budget * 0.15,
        )

    stage_2_result = state.tyler_stage_2_result
    if stage_2_result is None:
        raise ValueError(
            "Tyler Stage 6 requires a canonical Tyler Stage 2 EvidencePackage in PipelineState. "
            "Populate `state.tyler_stage_2_result` from the live pipeline or fixture artifacts "
            "instead of rebuilding it from the legacy EvidenceBundle."
        )
    stage_4_result = state.tyler_stage_4_result
    stage_5_result = state.tyler_stage_5_result

    decision_critical_claim_ids = {
        claim_id
        for dispute in stage_5_result.updated_dispute_queue
        if dispute.decision_critical
        for claim_id in dispute.claims_involved
    }
    grounded_claim_ids = {
        claim.id
        for claim in stage_5_result.updated_claim_ledger
        if claim.source_references
    }
    claim_ledger = [
        claim.model_dump(mode="json")
        for claim in stage_5_result.updated_claim_ledger
        if claim.id in grounded_claim_ids
    ]
    decision_critical_claim_ids = {
        claim_id for claim_id in decision_critical_claim_ids if claim_id in grounded_claim_ids
    }

    assessment_by_dispute = {
        assessment.dispute_id: assessment for assessment in stage_5_result.disputes_investigated
    }
    dispute_queue_context: list[dict[str, object]] = []
    for dispute in stage_5_result.updated_dispute_queue:
        assessment = assessment_by_dispute.get(dispute.id)
        remaining_uncertainty = ""
        if assessment:
            remaining_bits = [
                update.remaining_uncertainty
                for update in assessment.updated_claim_statuses
                if update.remaining_uncertainty
            ]
            remaining_uncertainty = "; ".join(bit for bit in remaining_bits if bit)
        dispute_queue_context.append(
            {
                **dispute.model_dump(mode="json"),
                "resolution_details": assessment.reasoning if assessment else "",
                "remaining_uncertainty": remaining_uncertainty or dispute.description,
            }
        )

    top_sources = _build_stage6_top_sources(
        bundle=state.evidence_bundle,
        verification_result=stage_5_result,
        top_sources_cap=int(parity_policy.get("stage6_top_sources_cap", 12)),
        non_dispute_summary_chars=int(
            parity_policy.get("stage6_non_dispute_source_summary_chars", 140)
        ),
    )

    evidence_gaps = list(
        dict.fromkeys(
            list(state.evidence_bundle.gaps)
            + [
                update.remaining_uncertainty
                for assessment in stage_5_result.disputes_investigated
                for update in assessment.updated_claim_statuses
                if update.remaining_uncertainty
            ]
        )
    )

    stage_3_results = list(state.tyler_stage_3_results)
    stage_3_summary = {
        "stage_name": "Stage 3: Independent Candidate Generation",
        "goal": "Produce independent recommendations, claims, assumptions, and counterarguments from the evidence package.",
        "key_findings": [
            f"{len(stage_3_results)} analysts succeeded",
            f"{sum(len(result.claims) for result in stage_3_results)} total Tyler analyst claims produced",
            "Independent analyst diversity preserved through aliasing and frame separation",
        ],
        "decisions_made": [
            "Preserved only successful Tyler Stage 3 analysis objects for synthesis context",
            "Kept analyst disagreement structure explicit for downstream Stage 4 extraction",
        ],
        "outcome": "Independent analysis objects available for canonicalization.",
        "reasoning": "Combined stage summary synthesized from successful Tyler Stage 3 analysis objects.",
    }
    all_stage_summaries = [
        tyler_stage1.stage_summary.model_dump(mode="json"),
        stage_2_result.stage_summary.model_dump(mode="json"),
        stage_3_summary,
        stage_4_result.stage_summary.model_dump(mode="json"),
        stage_5_result.stage_summary.model_dump(mode="json"),
    ]
    expected_process_summary_prefixes = _expected_process_summary_prefixes(
        all_stage_summaries
    )

    user_clarifications = "\n".join(state.user_guidance_notes)
    user_response_for_dispute = _build_stage6_user_response_map(
        dispute_queue=dispute_queue_context,
        user_clarifications=user_clarifications,
    )

    compacted_inputs = _compact_stage6_prompt_inputs(
        original_query=state.question.text,
        claim_ledger=claim_ledger,
        decision_critical_claim_ids=decision_critical_claim_ids,
        user_response_for_dispute=user_response_for_dispute,
        assumption_set=[assumption.model_dump(mode="json") for assumption in stage_4_result.assumption_set],
        dispute_queue=dispute_queue_context,
        top_sources=top_sources,
        evidence_gaps=evidence_gaps,
        all_stage_summaries=all_stage_summaries,
        char_limit=int(parity_policy.get("stage6_compaction_char_limit", 80000)),
        noncritical_claim_chars=int(parity_policy.get("stage6_noncritical_claim_chars", 180)),
        non_dispute_summary_chars=int(
            parity_policy.get("stage6_non_dispute_source_summary_chars", 140)
        ),
    )

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "tyler_v1_synthesis.yaml"),
        original_query=compacted_inputs["original_query"],
        claim_ledger=compacted_inputs["claim_ledger"],
        decision_critical_claim_ids=compacted_inputs["decision_critical_claim_ids"],
        user_response_for_dispute=compacted_inputs["user_response_for_dispute"],
        assumption_set=compacted_inputs["assumption_set"],
        dispute_queue=compacted_inputs["dispute_queue"],
        top_sources=compacted_inputs["top_sources"],
        evidence_gaps=compacted_inputs["evidence_gaps"],
        all_stage_summaries=compacted_inputs["all_stage_summaries"],
        response_schema_json=SynthesisReport.model_json_schema(),
    )

    unresolved_dispute_ids = {
        dispute.id
        for dispute in stage_5_result.updated_dispute_queue
        if dispute.status is not None and dispute.status.value == "unresolved"
    }
    synthesis_model, synthesis_fallback_models = _select_stage6_synthesis_model(state)

    async def _generate_once(feedback: list[str], suffix: str) -> SynthesisReport:
        prompt_messages = messages
        if feedback:
            prompt_messages = prompt_messages + [
                {
                    "role": "user",
                    "content": "Repair feedback for the previous draft:\n- " + "\n- ".join(feedback),
                }
            ]
        report, _meta = await acall_llm_structured(
            synthesis_model,
            prompt_messages,
            response_model=SynthesisReport,
            task="synthesis_tyler_v1",
            trace_id=f"{trace_id}/synthesis_tyler_v1{suffix}",
            max_budget=max_budget,
            fallback_models=synthesis_fallback_models,
        )
        return report

    report = await _generate_once(feedback=[], suffix="")
    repair_feedback = _validate_tyler_synthesis_report(
        report,
        unresolved_dispute_ids=unresolved_dispute_ids,
        verification_result=stage_5_result,
        bundle=state.evidence_bundle,
        expected_process_summary_prefixes=expected_process_summary_prefixes,
        min_tradeoffs=int(parity_policy.get("stage6_min_tradeoffs", 1)),
        min_preserved_alternatives=int(
            parity_policy.get("stage6_min_preserved_alternatives", 1)
        ),
        min_conditions_of_validity=int(
            parity_policy.get("stage6_min_conditions_of_validity", 1)
        ),
        max_conditional_markers=int(
            parity_policy.get("stage6_max_conditional_markers", 2)
        ),
    )
    if bool(parity_policy.get("stage6_repair_on_underfilled_fields", True)):
        max_repairs = int(parity_policy.get("stage6_repair_attempts", 1))
        for attempt in range(1, max_repairs + 1):
            if not repair_feedback:
                break
            _LOG.warning(
                "Tyler Stage 6 synthesis failed runtime validation; retrying. errors=%s",
                repair_feedback,
            )
            report = await _generate_once(
                feedback=repair_feedback,
                suffix=f"/repair_{attempt}",
            )
            repair_feedback = _validate_tyler_synthesis_report(
                report,
                unresolved_dispute_ids=unresolved_dispute_ids,
                verification_result=stage_5_result,
                bundle=state.evidence_bundle,
                expected_process_summary_prefixes=expected_process_summary_prefixes,
                min_tradeoffs=int(parity_policy.get("stage6_min_tradeoffs", 1)),
                min_preserved_alternatives=int(
                    parity_policy.get("stage6_min_preserved_alternatives", 1)
                ),
                min_conditions_of_validity=int(
                    parity_policy.get("stage6_min_conditions_of_validity", 1)
                ),
                max_conditional_markers=int(
                    parity_policy.get("stage6_max_conditional_markers", 2)
                ),
            )
    if repair_feedback and bool(parity_policy.get("stage6_fail_on_validation_error", True)):
        raise ValueError(
            "Tyler Stage 6 validation failed after repair: "
            + " | ".join(repair_feedback)
        )
    return report


def _render_tyler_structured_summary(report: SynthesisReport, original_query: str) -> str:
    """Render Tyler Stage 6 as a concise summary artifact."""
    lines = [
        f"# {original_query}",
        "",
        "## Executive Recommendation",
        "",
        report.executive_recommendation,
        "",
    ]

    if report.conditions_of_validity:
        lines.extend(["## Conditions Of Validity", ""])
        for condition in report.conditions_of_validity:
            lines.append(f"- {condition}")
        lines.append("")

    if report.decision_relevant_tradeoffs:
        lines.extend(["## Decision-Relevant Tradeoffs", ""])
        for tradeoff in report.decision_relevant_tradeoffs:
            lines.append(
                f"- If optimize for **{tradeoff.if_optimize_for}**: {tradeoff.then_recommend}"
            )
        lines.append("")

    if report.preserved_alternatives:
        lines.extend(["## Preserved Alternatives", ""])
        for alternative in report.preserved_alternatives:
            lines.append(
                f"- **{alternative.alternative}**: {alternative.conditions_for_preference}"
            )
        lines.append("")

    if report.disagreement_map:
        lines.extend(["## Disagreement Map", ""])
        for entry in report.disagreement_map:
            lines.append(f"- **{entry.dispute_id}** [{entry.type.value}] {entry.summary}")
        lines.append("")

    if report.claim_ledger_excerpt:
        lines.extend(["## Claim Ledger Excerpt", ""])
        for claim in report.claim_ledger_excerpt:
            lines.append(f"- **{claim.claim_id}** [{claim.final_status.value}] {claim.statement}")
        lines.append("")

    if report.evidence_gaps:
        lines.extend(["## Evidence Gaps", ""])
        for gap in report.evidence_gaps:
            lines.append(f"- {gap}")
        lines.append("")

    return "\n".join(lines)


async def render_long_report(
    state: PipelineState,
    trace_id: str,
    max_budget: float = 2.0,
) -> str:
    """Render the canonical long-form report directly from Tyler Stage 6."""
    del trace_id, max_budget
    if state.tyler_stage_6_result is None or state.question is None:
        raise ValueError(
            "Canonical long-report rendering requires `state.tyler_stage_6_result` and "
            "`state.question`. Generate Tyler Stage 6 before calling render_long_report()."
        )
    return render_tyler_synthesis_markdown(
        state.tyler_stage_6_result,
        original_query=state.question.text,
    )


def write_outputs(
    state: PipelineState,
    output_dir: Path,
    long_report_md: str | None = None,
    *,
    observability_db_path: Path | None = None,
    trace_id_root: str | None = None,
) -> dict[str, Path]:
    """Write canonical Tyler-native output artifacts to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    paths["trace"] = write_tyler_trace(
        state,
        output_dir,
        observability_db_path=observability_db_path,
        trace_id_root=trace_id_root,
    )

    if long_report_md:
        report_path = output_dir / "report.md"
        report_path.write_text(long_report_md)
        paths["report"] = report_path

    if state.tyler_stage_6_result is not None and state.question is not None:
        summary_path = output_dir / "summary.md"
        summary_path.write_text(
            _render_tyler_structured_summary(
                state.tyler_stage_6_result,
                state.question.text,
            )
        )
        paths["summary"] = summary_path

    if state.tyler_handoff is not None:
        handoff = state.tyler_handoff
    elif (
        state.question is not None
        and state.tyler_stage_2_result is not None
        and state.tyler_stage_5_result is not None
        and state.tyler_stage_6_result is not None
    ):
        handoff = build_tyler_downstream_handoff(state)
    else:
        handoff = None

    if handoff is not None:
        handoff_path = output_dir / "handoff.json"
        handoff_path.write_text(handoff.model_dump_json(indent=2))
        paths["handoff"] = handoff_path

    return paths
