"""Grounded export and downstream handoff.

Phase 5: Two-step report generation:
1. Structured FinalReport for grounding validation (fast, cheap)
2. Long-form markdown report from full pipeline state (the actual deliverable)

The structured report ensures every claim is grounded. The long-form
report is what the user reads — a thorough, publication-quality analysis.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from grounded_research.config import (
    get_evidence_policy_config,
    get_export_policy_config,
    get_fallback_models,
    get_model,
)
from grounded_research.models import (
    ClaimLedger,
    DownstreamHandoff,
    EvidenceBundle,
    FinalReport,
    PipelineState,
    PipelineWarning,
)
from grounded_research.runtime_policy import get_request_timeout

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LOG = logging.getLogger(__name__)
_PLACEHOLDER_PATTERNS = (
    re.compile(r"\bX-Y%?\b"),
    re.compile(r"\bN=\?\b"),
    re.compile(r"\bTBD\b", re.IGNORECASE),
    re.compile(r"\[insert[^\]]*\]", re.IGNORECASE),
)


def _parse_word_target_upper_bound(word_target: str) -> int:
    """Parse the upper bound from a display word target like `10,000-15,000`."""
    numbers = [int(part.replace(",", "")) for part in re.findall(r"\d[\d,]*", word_target)]
    if not numbers:
        return 0
    return max(numbers)


def _should_use_sectioned_synthesis(depth_name: str, word_target: str) -> bool:
    """Decide whether long-report rendering should use section composition."""
    export_policy = get_export_policy_config()
    enabled_depths = {
        str(depth).strip()
        for depth in export_policy.get("sectioned_synthesis_enabled_depths", [])
    }
    min_target = int(export_policy.get("sectioned_synthesis_min_word_target", 9000))
    return depth_name in enabled_depths and _parse_word_target_upper_bound(word_target) >= min_target


def _build_section_specs(
    *,
    optimization_axes: list[str],
    sub_questions: list[dict[str, object]],
) -> list[dict[str, str]]:
    """Build the ordered section plan for sectioned long-report synthesis."""
    export_policy = get_export_policy_config()
    max_distinctions = int(export_policy.get("sectioned_synthesis_max_distinction_sections", 4))

    section_specs: list[dict[str, str]] = [
        {
            "kind": "intro",
            "title": "Title, executive summary, and framing",
            "brief": (
                "Write the report title, executive summary, why the question matters, "
                "and the key distinctions that organize the rest of the analysis."
            ),
        }
    ]

    distinction_axes = optimization_axes[:max_distinctions]
    if distinction_axes:
        for axis in distinction_axes:
            section_specs.append({
                "kind": "distinction",
                "title": axis,
                "brief": (
                    f"Analyze this key distinction in depth: {axis}. Present the strongest "
                    "evidence, named studies or programs, disagreements, and the most "
                    "defensible reading of the evidence."
                ),
            })
    else:
        fallback_titles = [
            "What the strongest direct evidence shows",
            "Reconciling the contradictory cases",
            "Broader implications and decision significance",
        ]
        fallback_briefs = [
            "Cover the strongest direct evidence, major studies, pilots, and quantitative findings.",
            "Explain why apparently conflicting findings can all be true in different contexts.",
            "Connect the evidence to broader institutional, macro, and decision-relevant implications.",
        ]
        for idx, title in enumerate(fallback_titles[:max_distinctions]):
            if idx < len(sub_questions):
                sq_text = str(sub_questions[idx].get("text", ""))
                brief = (
                    f"Center this section on the sub-question `{sq_text}` while still building "
                    "a coherent argument from the strongest relevant claims and evidence."
                )
            else:
                brief = fallback_briefs[idx]
            section_specs.append({
                "kind": "distinction",
                "title": title,
                "brief": brief,
            })

    section_specs.append({
        "kind": "final",
        "title": "Contradictions, implications, verdict, and alternatives",
        "brief": (
            "Write the remaining closing sections: reconciling contradictions when needed, "
            "broader implications, what the evidence does not tell us, the verdict, "
            "alternatives and when to choose them, what would change the recommendation, "
            "and the closing summary."
        ),
    })
    return section_specs


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

    model = get_model("synthesis")

    async def _generate_once(
        repair_feedback: list[str],
        trace_suffix: str,
    ) -> FinalReport:
        evidence_policy = get_evidence_policy_config()
        messages = render_prompt(
            str(_PROJECT_ROOT / "prompts" / "synthesis.yaml"),
            question=state.question.model_dump(),
            evidence=[e.model_dump() for e in state.evidence_bundle.evidence],
            claims=[c.model_dump() for c in state.claim_ledger.claims],
            disputes=[d.model_dump() for d in state.claim_ledger.disputes],
            arbitration_results=[a.model_dump() for a in state.claim_ledger.arbitration_results],
            evidence_gaps=state.evidence_bundle.gaps,
            validation_feedback=repair_feedback,
            synthesis_evidence_cap=int(evidence_policy["synthesis_evidence_cap"]),
            structured_content_truncation_chars=int(
                evidence_policy["structured_content_truncation_chars"]
            ),
        )
        report, _meta = await acall_llm_structured(
            model,
            messages,
            response_model=FinalReport,
            task="report_synthesis",
            trace_id=f"{trace_id}/synthesis{trace_suffix}",
            timeout=get_request_timeout("synthesis"),
            max_budget=max_budget,
            fallback_models=get_fallback_models("synthesis"),
        )
        return report

    report = await _generate_once(repair_feedback=[], trace_suffix="")

    # Strip hallucinated claim IDs that the LLM invented
    valid_claim_ids = {c.id for c in state.claim_ledger.claims}
    hallucinated = [cid for cid in report.cited_claim_ids if cid not in valid_claim_ids]
    if hallucinated:
        import logging
        logging.getLogger(__name__).warning(
            "Synthesis hallucinated %d claim IDs, stripping: %s", len(hallucinated), hallucinated
        )
        report.cited_claim_ids = [cid for cid in report.cited_claim_ids if cid in valid_claim_ids]

    grounding_errors = validate_grounding(report, state.claim_ledger, state.evidence_bundle)
    if grounding_errors:
        _LOG.warning(
            "Structured report grounding validation failed; retrying once. errors=%s",
            grounding_errors,
        )
        repaired = await _generate_once(
            repair_feedback=grounding_errors,
            trace_suffix="/repair_1",
        )
        hallucinated = [cid for cid in repaired.cited_claim_ids if cid not in valid_claim_ids]
        if hallucinated:
            _LOG.warning(
                "Structured report repair hallucinated %d claim IDs, stripping: %s",
                len(hallucinated),
                hallucinated,
            )
            repaired.cited_claim_ids = [cid for cid in repaired.cited_claim_ids if cid in valid_claim_ids]
        report = repaired

    return report


def _find_long_report_quality_issues(markdown: str) -> list[str]:
    """Return mechanically detectable long-report quality defects."""
    issues: list[str] = []
    for pattern in _PLACEHOLDER_PATTERNS:
        if pattern.search(markdown):
            issues.append(f"Remove symbolic placeholder token matching `{pattern.pattern}`.")
    return issues


async def render_long_report(
    state: PipelineState,
    trace_id: str,
    max_budget: float = 2.0,
    decomposition: "QuestionDecomposition | None" = None,
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

    from grounded_research.config import get_depth_config, load_config

    # Pass decomposition context if available
    sub_questions = []
    optimization_axes = []
    if decomposition is not None:
        sub_questions = [sq.model_dump() for sq in decomposition.sub_questions]
        optimization_axes = decomposition.optimization_axes

    # Synthesis mode and depth from config
    config = load_config()
    evidence_policy = get_evidence_policy_config()
    synthesis_mode = config.get("synthesis_mode", "grounded")
    depth = get_depth_config()
    depth_name = str(config.get("depth", "standard"))
    word_target = depth.get("synthesis_word_target", "5,000-6,000")

    model = get_model("synthesis")

    async def _render_once(
        repair_feedback: list[str],
        trace_suffix: str,
        *,
        section_mode: bool = False,
        section_kind: str = "",
        section_title: str = "",
        section_brief: str = "",
        section_position: int = 1,
        section_count: int = 1,
    ) -> str:
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
            word_target=word_target,
            sub_questions=sub_questions,
            optimization_axes=optimization_axes,
            repair_feedback=repair_feedback,
            section_mode=section_mode,
            section_kind=section_kind,
            section_title=section_title,
            section_brief=section_brief,
            section_position=section_position,
            section_count=section_count,
            long_report_content_truncation_chars=int(
                evidence_policy["long_report_content_truncation_chars"]
            ),
        )
        result = await acall_llm(
            model,
            messages,
            task="long_report_synthesis",
            trace_id=f"{trace_id}/long_report{trace_suffix}",
            timeout=get_request_timeout("long_report"),
            max_budget=max_budget,
            fallback_models=get_fallback_models("synthesis"),
        )
        return result.content

    async def _render_sectioned_report(repair_feedback: list[str], trace_suffix: str) -> str:
        section_specs = _build_section_specs(
            optimization_axes=optimization_axes,
            sub_questions=sub_questions,
        )
        rendered_sections: list[str] = []
        per_section_budget = max_budget / max(1, len(section_specs))
        for idx, section_spec in enumerate(section_specs, start=1):
            section_markdown = await _render_once(
                repair_feedback=repair_feedback,
                trace_suffix=f"{trace_suffix}/section_{idx}",
                section_mode=True,
                section_kind=section_spec["kind"],
                section_title=section_spec["title"],
                section_brief=section_spec["brief"],
                section_position=idx,
                section_count=len(section_specs),
            )
            rendered_sections.append(section_markdown.strip())
        return "\n\n".join(section for section in rendered_sections if section)

    if _should_use_sectioned_synthesis(depth_name, word_target):
        markdown = await _render_sectioned_report(repair_feedback=[], trace_suffix="")
    else:
        markdown = await _render_once(repair_feedback=[], trace_suffix="")

    issues = _find_long_report_quality_issues(markdown)
    if issues:
        _LOG.warning(
            "Long report quality validation failed; retrying once. issues=%s",
            issues,
        )
        if _should_use_sectioned_synthesis(depth_name, word_target):
            markdown = await _render_sectioned_report(
                repair_feedback=issues,
                trace_suffix="/repair_1",
            )
        else:
            markdown = await _render_once(repair_feedback=issues, trace_suffix="/repair_1")

    return markdown


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
