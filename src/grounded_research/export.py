"""Grounded export and downstream handoff.

Phase 5: Renders the adjudicated state into a FinalReport, validates
grounding, and writes report.md + trace.json + handoff.json.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from grounded_research.config import get_model
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

    # Rule 1: Every cited claim exists in ledger
    for cid in report.cited_claim_ids:
        if ledger.claim_by_id(cid) is None:
            errors.append(f"Cited claim {cid} not found in ledger")

    # Rule 2: Every cited claim has evidence backing
    for cid in report.cited_claim_ids:
        claim = ledger.claim_by_id(cid)
        if claim and not claim.evidence_ids:
            errors.append(f"Cited claim {cid} has no evidence_ids")

    # Rule 3: Every evidence ID on cited claims resolves
    for cid in report.cited_claim_ids:
        claim = ledger.claim_by_id(cid)
        if claim:
            for eid in claim.evidence_ids:
                if eid not in evidence_ids:
                    errors.append(f"Claim {cid} cites evidence {eid} not in bundle")

    # Rule 4: Unresolved disputes appear in report
    for d in ledger.unresolved_disputes():
        if d.id not in report.disagreement_summary:
            errors.append(f"Unresolved dispute {d.id} not mentioned in report")

    return errors


async def generate_report(
    state: PipelineState,
    trace_id: str,
    max_budget: float = 1.0,
) -> FinalReport:
    """Generate the final report from pipeline state via LLM synthesis."""
    from llm_client import acall_llm_structured, render_prompt

    assert state.claim_ledger is not None
    assert state.evidence_bundle is not None
    assert state.question is not None

    messages = render_prompt(
        str(_PROJECT_ROOT / "prompts" / "synthesis.yaml"),
        question=state.question.model_dump(),
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
    )

    return report


def write_outputs(
    state: PipelineState,
    output_dir: Path,
) -> dict[str, Path]:
    """Write all output artifacts to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    # trace.json — full pipeline state
    trace_path = output_dir / "trace.json"
    trace_path.write_text(state.model_dump_json(indent=2))
    paths["trace"] = trace_path

    # report.md — human-readable report
    if state.report:
        report_path = output_dir / "report.md"
        md = _render_report_markdown(state.report, state.claim_ledger)
        report_path.write_text(md)
        paths["report"] = report_path

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


def _render_report_markdown(report: FinalReport, ledger: ClaimLedger | None) -> str:
    """Render a FinalReport as markdown."""
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
