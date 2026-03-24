"""Grounded export and downstream handoff.

Phase 5: Two-step report generation:
1. Structured FinalReport for grounding validation (fast, cheap)
2. Long-form markdown report from full pipeline state (the actual deliverable)

The structured report ensures every claim is grounded. The long-form
report is what the user reads — a thorough, publication-quality analysis.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from grounded_research.config import get_fallback_models, get_model
from grounded_research.models import (
    ClaimLedger,
    DownstreamHandoff,
    EvidenceBundle,
    FinalReport,
    PipelineState,
    PipelineWarning,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def validate_grounding(
    report: FinalReport,
    ledger: ClaimLedger,
    bundle: EvidenceBundle,
) -> list[str]:
    """Validate that the report is grounded in the ledger and evidence.

    Returns a list of grounding errors. Empty list = all checks pass.
    """
    errors: list[str] = []
    evidence_ids = {e.id for e in bundle.evidence}

    for cid in report.cited_claim_ids:
        if ledger.claim_by_id(cid) is None:
            errors.append(f"Cited claim {cid} not found in ledger")

    for cid in report.cited_claim_ids:
        claim = ledger.claim_by_id(cid)
        if claim and not claim.evidence_ids:
            errors.append(f"Cited claim {cid} has no evidence_ids")

    for cid in report.cited_claim_ids:
        claim = ledger.claim_by_id(cid)
        if claim:
            for eid in claim.evidence_ids:
                if eid not in evidence_ids:
                    errors.append(f"Claim {cid} cites evidence {eid} not in bundle")

    for d in ledger.unresolved_disputes():
        if d.id not in report.disagreement_summary:
            errors.append(f"Unresolved dispute {d.id} not mentioned in report")

    return errors


async def generate_report(
    state: PipelineState,
    trace_id: str,
    max_budget: float = 1.0,
) -> FinalReport:
    """Generate the structured FinalReport for grounding validation."""
    from llm_client import acall_llm_structured, render_prompt

    assert state.claim_ledger is not None
    assert state.evidence_bundle is not None
    assert state.question is not None

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "synthesis.yaml"),
        question=state.question.model_dump(),
        evidence=[e.model_dump() for e in state.evidence_bundle.evidence],
        claims=[c.model_dump() for c in state.claim_ledger.claims],
        disputes=[d.model_dump() for d in state.claim_ledger.disputes],
        arbitration_results=[a.model_dump() for a in state.claim_ledger.arbitration_results],
        evidence_gaps=state.evidence_bundle.gaps,
    )

    model = get_model("synthesis")
    report, _meta = await acall_llm_structured(
        model,
        messages,
        response_model=FinalReport,
        task="report_synthesis",
        trace_id=f"{trace_id}/synthesis",
        max_budget=max_budget,
        fallback_models=get_fallback_models("synthesis"),
    )

    # Strip hallucinated claim IDs that the LLM invented
    valid_claim_ids = {c.id for c in state.claim_ledger.claims}
    hallucinated = [cid for cid in report.cited_claim_ids if cid not in valid_claim_ids]
    if hallucinated:
        import logging
        logging.getLogger(__name__).warning(
            "Synthesis hallucinated %d claim IDs, stripping: %s", len(hallucinated), hallucinated
        )
        report.cited_claim_ids = [cid for cid in report.cited_claim_ids if cid in valid_claim_ids]

    return report


async def render_long_report(
    state: PipelineState,
    trace_id: str,
    max_budget: float = 2.0,
    decomposition: object | None = None,
) -> str:
    """Render the full long-form research report as markdown.

    This is the actual deliverable — a thorough, publication-quality
    analysis with detailed evidence discussion, dispute analysis, and
    nuanced recommendations. Targets 3,000-6,000 words.

    Uses the full pipeline state (all evidence, claims, disputes,
    arbitration results, sources) as context for the synthesis LLM.
    """
    from llm_client import acall_llm, render_prompt

    assert state.claim_ledger is not None
    assert state.evidence_bundle is not None
    assert state.question is not None

    from grounded_research.config import load_config

    # Pass decomposition context if available
    sub_questions = []
    optimization_axes = []
    if decomposition is not None:
        sub_questions = [sq.model_dump() for sq in decomposition.sub_questions]
        optimization_axes = decomposition.optimization_axes

    # Synthesis mode from config
    config = load_config()
    synthesis_mode = config.get("synthesis_mode", "grounded")

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "long_report.yaml"),
        question=state.question.model_dump(),
        sources=[s.model_dump() for s in state.evidence_bundle.sources],
        evidence=[e.model_dump() for e in state.evidence_bundle.evidence],
        claims=[c.model_dump() for c in state.claim_ledger.claims],
        disputes=[d.model_dump() for d in state.claim_ledger.disputes],
        arbitration_results=[a.model_dump() for a in state.claim_ledger.arbitration_results],
        evidence_gaps=state.evidence_bundle.gaps,
        analyst_count=len([r for r in state.analyst_runs if r.succeeded]),
        synthesis_mode=synthesis_mode,
        sub_questions=sub_questions,
        optimization_axes=optimization_axes,
    )

    model = get_model("synthesis")
    result = await acall_llm(
        model,
        messages,
        task="long_report_synthesis",
        trace_id=f"{trace_id}/long_report",
        max_budget=max_budget,
        fallback_models=get_fallback_models("synthesis"),
    )

    return result.content


def write_outputs(
    state: PipelineState,
    output_dir: Path,
    long_report_md: str | None = None,
) -> dict[str, Path]:
    """Write all output artifacts to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    # trace.json — full pipeline state
    trace_path = output_dir / "trace.json"
    trace_path.write_text(state.model_dump_json(indent=2))
    paths["trace"] = trace_path

    # report.md — the long-form report (primary deliverable)
    if long_report_md:
        report_path = output_dir / "report.md"
        report_path.write_text(long_report_md)
        paths["report"] = report_path
    elif state.report:
        # Fallback to structured report rendering if long-form not available
        report_path = output_dir / "report.md"
        md = _render_structured_report(state.report, state.claim_ledger)
        report_path.write_text(md)
        paths["report"] = report_path

    # summary.md — the structured report as a quick reference
    if state.report:
        summary_path = output_dir / "summary.md"
        md = _render_structured_report(state.report, state.claim_ledger)
        summary_path.write_text(md)
        paths["summary"] = summary_path

    # handoff.json — downstream artifact for onto-canon
    if state.claim_ledger and state.evidence_bundle and state.question:
        handoff = DownstreamHandoff(
            question=state.question,
            claim_ledger=state.claim_ledger,
            sources=state.evidence_bundle.sources,
            evidence=state.evidence_bundle.evidence,
        )
        handoff_path = output_dir / "handoff.json"
        handoff_path.write_text(handoff.model_dump_json(indent=2))
        paths["handoff"] = handoff_path

    return paths


def _render_structured_report(report: FinalReport, ledger: ClaimLedger | None) -> str:
    """Render a structured FinalReport as markdown (summary format)."""
    lines = [
        f"# {report.title}",
        "",
        f"**Question:** {report.question}",
        f"**Generated:** {report.generated_at.isoformat()}",
        "",
        "## Recommendation",
        "",
        report.recommendation,
        "",
    ]

    if report.alternatives:
        lines.extend(["## Alternatives", ""])
        for alt in report.alternatives:
            lines.append(f"- {alt}")
        lines.append("")

    if report.disagreement_summary:
        lines.extend(["## Disagreement Summary", "", report.disagreement_summary, ""])

    if report.evidence_gaps:
        lines.extend(["## Evidence Gaps", ""])
        for gap in report.evidence_gaps:
            lines.append(f"- {gap}")
        lines.append("")

    if report.flip_conditions:
        lines.extend(["## Conditions That Would Change This Recommendation", ""])
        for cond in report.flip_conditions:
            lines.append(f"- {cond}")
        lines.append("")

    if report.cited_claim_ids and ledger:
        lines.extend(["## Cited Claims", ""])
        for cid in report.cited_claim_ids:
            claim = ledger.claim_by_id(cid)
            if claim:
                lines.append(f"- **{cid}** [{claim.status}]: {claim.statement}")
        lines.append("")

    return "\n".join(lines)
