"""Grounded Research Adjudication Engine.

End-to-end pipeline: Ingest → Analyze → Canonicalize → Adjudicate → Export.

Usage:
    python engine.py "research question" --evidence PATH [--output-dir PATH]
    python engine.py --fixture PATH [--output-dir PATH]
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from grounded_research.config import get_budget, load_config
from grounded_research.models import PipelineState, PhaseTrace


async def run_pipeline(
    fixture_path: Path,
    output_dir: Path,
    decomposition: object | None = None,
) -> PipelineState:
    """Run the full adjudication pipeline."""
    from grounded_research.ingest import load_manual_bundle, validate_bundle
    from grounded_research.analysts import run_analysts
    from grounded_research.canonicalize import (
        extract_raw_claims,
        deduplicate_claims,
        detect_disputes,
        build_ledger,
    )
    from grounded_research.verify import verify_disputes
    from grounded_research.export import generate_report, render_long_report, validate_grounding, write_outputs

    run_id = uuid.uuid4().hex[:12]
    trace_id = f"pipeline/{run_id}"
    state = PipelineState(run_id=run_id)

    config = load_config()
    total_budget = get_budget("pipeline_max_budget_usd")

    print(f"=== Grounded Research Adjudication Engine ===")
    print(f"Run ID: {run_id}")
    print(f"Budget: ${total_budget:.2f}")
    print()

    try:
        # --- Phase 1: Ingest ---
        phase_start = datetime.now(timezone.utc)
        state.current_phase = "ingest"
        print("[Phase 1] Ingesting evidence bundle...")

        bundle = load_manual_bundle(fixture_path)
        warnings = validate_bundle(bundle)
        for w in warnings:
            state.add_warning("ingest", "validation", w)

        state.question = bundle.question
        state.evidence_bundle = bundle

        state.phase_traces.append(PhaseTrace(
            phase="ingest",
            started_at=phase_start,
            completed_at=datetime.now(timezone.utc),
            succeeded=True,
            output_summary=f"{len(bundle.sources)} sources, {len(bundle.evidence)} evidence items, {len(bundle.gaps)} gaps",
        ))
        print(f"  Sources: {len(bundle.sources)}, Evidence: {len(bundle.evidence)}, Gaps: {len(bundle.gaps)}")

        # --- Evidence sufficiency check (if decomposition available) ---
        if decomposition is not None:
            from collections import Counter
            sq_coverage = Counter(e.sub_question_id for e in bundle.evidence if e.sub_question_id)
            for sq in decomposition.sub_questions:
                count = sq_coverage.get(sq.id, 0)
                if count < 2:
                    gap_msg = f"Sub-question '{sq.text[:60]}...' has only {count} evidence items (minimum 2)"
                    bundle.gaps.append(gap_msg)
                    state.add_warning("ingest", "evidence_sufficiency", gap_msg)
                    print(f"  GAP: {gap_msg}")

        # --- Evidence compression (if over threshold) ---
        from grounded_research.compress import compress_evidence
        compression_threshold = config.get("evidence_policy", {}).get("compression_threshold", 80)
        removed = compress_evidence(bundle, threshold=compression_threshold)
        if removed > 0:
            print(f"  Compressed evidence: removed {removed} items, {len(bundle.evidence)} remaining")

        # --- Phase 2: Analyze ---
        phase_start = datetime.now(timezone.utc)
        state.current_phase = "analyze"
        print("\n[Phase 2] Running 3 independent analysts...")

        analyst_runs = await run_analysts(bundle, trace_id, decomposition=decomposition)
        state.analyst_runs = analyst_runs

        succeeded = [r for r in analyst_runs if r.succeeded]

        # Evidence-label leakage check (#30)
        import re
        url_pattern = re.compile(r'https?://\S+')
        for run in succeeded:
            for claim in run.claims:
                urls_in_claim = url_pattern.findall(claim.statement)
                if urls_in_claim:
                    state.add_warning(
                        "analyze", "evidence_leakage",
                        f"Analyst {run.analyst_label} claim {claim.id} contains URL(s): {urls_in_claim[:2]}"
                    )
            urls_in_summary = url_pattern.findall(run.summary)
            if urls_in_summary:
                state.add_warning(
                    "analyze", "evidence_leakage",
                    f"Analyst {run.analyst_label} summary contains URL(s): {urls_in_summary[:2]}"
                )

        state.phase_traces.append(PhaseTrace(
            phase="analyze",
            started_at=phase_start,
            completed_at=datetime.now(timezone.utc),
            succeeded=True,
            llm_calls=len(analyst_runs),
            output_summary=f"{len(succeeded)}/{len(analyst_runs)} analysts succeeded, {sum(len(r.claims) for r in succeeded)} total claims",
        ))
        for r in analyst_runs:
            status = f"OK ({len(r.claims)} claims)" if r.succeeded else f"FAILED: {r.error}"
            print(f"  {r.analyst_label} ({r.model}): {status}")

        # --- Phase 3a: Claim extraction ---
        phase_start = datetime.now(timezone.utc)
        state.current_phase = "canonicalize"
        print("\n[Phase 3a] Extracting raw claims...")

        valid_evidence_ids = {e.id for e in bundle.evidence}
        raw_claims, claim_to_analyst = extract_raw_claims(analyst_runs, valid_evidence_ids)
        print(f"  Raw claims: {len(raw_claims)}")

        # --- Phase 3b: Deduplication ---
        print("[Phase 3b] Deduplicating claims...")

        canonical_claims = await deduplicate_claims(
            raw_claims, claim_to_analyst, trace_id, max_budget=total_budget * 0.1,
        )
        print(f"  Canonical claims: {len(canonical_claims)} (from {len(raw_claims)} raw)")

        # --- Phase 3c: Dispute detection ---
        print("[Phase 3c] Detecting disputes...")

        disputes = await detect_disputes(
            canonical_claims, trace_id, max_budget=total_budget * 0.1,
        )
        ledger = build_ledger(canonical_claims, disputes)
        state.claim_ledger = ledger

        state.phase_traces.append(PhaseTrace(
            phase="canonicalize",
            started_at=phase_start,
            completed_at=datetime.now(timezone.utc),
            succeeded=True,
            llm_calls=2,
            output_summary=f"{len(canonical_claims)} claims, {len(disputes)} disputes ({len(ledger.decision_critical_disputes())} decision-critical)",
        ))
        print(f"  Disputes: {len(disputes)} ({len(ledger.decision_critical_disputes())} decision-critical)")

        # --- User steering (preference/ambiguity disputes) ---
        preference_disputes = [
            d for d in disputes
            if d.dispute_type in ("preference_conflict", "ambiguity") and not d.resolved
        ]
        if preference_disputes and sys.stdin.isatty():
            print(f"\n[Steering] {len(preference_disputes)} preference/ambiguity disputes found.")
            for d in preference_disputes[:2]:  # max 2 questions
                print(f"\n  {d.id} [{d.dispute_type}]: {d.description[:120]}...")
                print(f"  Claims: {d.claim_ids}")
                try:
                    answer = input("  Your guidance (or Enter to skip): ").strip()
                    if answer:
                        d.resolution_summary = f"User guidance: {answer}"
                        d.resolved = True
                        print(f"  → Recorded.")
                except (EOFError, KeyboardInterrupt):
                    print(f"  → Skipped.")

        # --- Phase 4: Verification ---
        phase_start = datetime.now(timezone.utc)
        state.current_phase = "adjudicate"
        print("\n[Phase 4] Verifying decision-critical disputes...")

        max_disputes = int(get_budget("verification_max_disputes"))
        ledger, arb_results, adjudication_warnings, phase4_llm_calls = await verify_disputes(
            ledger, bundle, trace_id,
            max_disputes=max_disputes,
            max_budget=total_budget * 0.3,
        )
        state.claim_ledger = ledger
        for warning in adjudication_warnings:
            state.add_warning(
                "adjudicate",
                warning.code,
                warning.message,
                **warning.context,
            )

        state.phase_traces.append(PhaseTrace(
            phase="adjudicate",
            started_at=phase_start,
            completed_at=datetime.now(timezone.utc),
            succeeded=True,
            llm_calls=phase4_llm_calls,
            output_summary=f"{len(arb_results)} disputes arbitrated, {len(adjudication_warnings)} adjudication warnings",
        ))
        for ar in arb_results:
            print(f"  {ar.dispute_id} → {ar.verdict}")

        # --- Phase 5: Export ---
        phase_start = datetime.now(timezone.utc)
        state.current_phase = "export"
        print("\n[Phase 5] Generating grounded report...")

        report = await generate_report(state, trace_id, max_budget=total_budget * 0.1)
        state.report = report

        # Grounding validation
        grounding_errors = validate_grounding(report, ledger, bundle)
        if grounding_errors:
            for err in grounding_errors:
                state.add_warning("export", "grounding", err)
                print(f"  GROUNDING WARNING: {err}")

        state.phase_traces.append(PhaseTrace(
            phase="export",
            started_at=phase_start,
            completed_at=datetime.now(timezone.utc),
            succeeded=True,
            llm_calls=1,
            output_summary=f"Report with {len(report.cited_claim_ids)} cited claims, {len(grounding_errors)} grounding warnings",
        ))

        # Render long-form report
        print("  Rendering long-form report (3,000-6,000 words)...")
        long_report_md = await render_long_report(
            state, trace_id, max_budget=total_budget * 0.2,
            decomposition=decomposition,
        )
        print(f"  Long report: {len(long_report_md)} chars, ~{len(long_report_md.split())} words")

        state.phase_traces[-1].llm_calls = 2  # structured + long-form
        state.phase_traces[-1].output_summary = (
            f"Structured report: {len(report.cited_claim_ids)} cited claims, "
            f"{len(grounding_errors)} grounding warnings. "
            f"Long report: ~{len(long_report_md.split())} words."
        )

        # Mark complete before writing so trace.json reflects final state
        state.current_phase = "complete"
        state.success = True
        state.completed_at = datetime.now(timezone.utc)

        # Write outputs
        paths = write_outputs(state, output_dir, long_report_md=long_report_md)
        for name, path in paths.items():
            print(f"  Wrote: {path}")

        print(f"\n=== Pipeline complete ===")
        print(f"Report: {report.title}")
        print(f"Long report: ~{len(long_report_md.split())} words")
        print(f"Cited claims: {len(report.cited_claim_ids)}")
        print(f"Grounding warnings: {len(grounding_errors)}")
        print(f"Pipeline warnings: {len(state.warnings)}")

    except Exception as e:
        state.current_phase = "failed"
        state.success = False
        state.completed_at = datetime.now(timezone.utc)
        state.add_warning("failed", "pipeline_error", str(e))

        # Write partial trace even on failure
        output_dir.mkdir(parents=True, exist_ok=True)
        trace_path = output_dir / "trace.json"
        trace_path.write_text(state.model_dump_json(indent=2))
        print(f"\n=== Pipeline FAILED ===")
        print(f"Error: {e}")
        print(f"Partial trace: {trace_path}")
        raise

    return state


async def run_pipeline_from_question(
    question: str,
    output_dir: Path,
) -> PipelineState:
    """Run the full pipeline starting from a question (collects evidence automatically)."""
    from grounded_research.collect import collect_evidence
    from grounded_research.decompose import decompose_with_validation

    run_id = uuid.uuid4().hex[:12]
    trace_id = f"pipeline/{run_id}"

    # --- Decompose question into sub-questions (with validation) ---
    print(f"=== Question Decomposition ===")
    print(f"Raw question: {question}")
    print()

    decomposition, validation = await decompose_with_validation(question, trace_id)
    print(f"  Core question: {decomposition.core_question[:80]}...")
    print(f"  Sub-questions: {len(decomposition.sub_questions)}")
    for sq in decomposition.sub_questions:
        print(f"    [{sq.type}] {sq.text[:70]}...")
    print(f"  Optimization axes: {decomposition.optimization_axes}")
    if decomposition.ambiguous_terms:
        print(f"  Ambiguous terms: {len(decomposition.ambiguous_terms)}")
        for at in decomposition.ambiguous_terms:
            print(f"    '{at.term}' → {at.chosen_interpretation} (not: {at.alternative})")
    if validation:
        print(f"  Validation: {validation.verdict}")
        if validation.coverage_gaps:
            print(f"    Coverage gaps: {validation.coverage_gaps}")
        if validation.bias_flags:
            print(f"    Bias flags: {validation.bias_flags}")
        if validation.granularity_issues:
            print(f"    Granularity: {validation.granularity_issues}")
    print()

    # --- Collect evidence with sub-question-driven search ---
    print(f"=== Evidence Collection ===")
    print(f"Question: {decomposition.core_question}")
    print()

    sub_questions_dicts = [sq.model_dump() for sq in decomposition.sub_questions]
    bundle = await collect_evidence(
        decomposition.core_question, trace_id,
        sub_questions=sub_questions_dicts,
    )

    # Save the collected bundle for reuse
    bundle_path = output_dir / "collected_bundle.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(bundle.model_dump_json(indent=2))
    print(f"  Saved bundle: {bundle_path}")

    # Save decomposition for pipeline use
    import json
    decomp_path = output_dir / "decomposition.json"
    decomp_path.write_text(decomposition.model_dump_json(indent=2))
    print(f"  Saved decomposition: {decomp_path}")
    print()

    return await run_pipeline(bundle_path, output_dir, decomposition=decomposition)


def main() -> None:
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Grounded Research Adjudication Engine")
    parser.add_argument(
        "question",
        nargs="?",
        default=None,
        help="Research question (if provided, evidence is collected automatically)",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="Path to pre-built evidence bundle JSON (skips collection)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for report, trace, and handoff",
    )
    parser.add_argument(
        "--decomposition",
        type=Path,
        default=None,
        help="Path to decomposition JSON (pairs with --fixture)",
    )
    args = parser.parse_args()

    if args.question:
        slug = args.question[:40].lower().replace(" ", "_").replace("?", "")
        out_dir = args.output_dir or (PROJECT_ROOT / "output" / slug)
        asyncio.run(run_pipeline_from_question(args.question, out_dir))
    elif args.fixture:
        out_dir = args.output_dir or (PROJECT_ROOT / "output" / "pipeline")
        # Load decomposition if provided alongside fixture
        decomp = None
        if args.decomposition and args.decomposition.exists():
            from grounded_research.models import QuestionDecomposition
            decomp = QuestionDecomposition.model_validate_json(args.decomposition.read_text())
        elif args.fixture.parent.joinpath("decomposition.json").exists():
            # Auto-detect decomposition in same directory as fixture
            from grounded_research.models import QuestionDecomposition
            decomp = QuestionDecomposition.model_validate_json(
                args.fixture.parent.joinpath("decomposition.json").read_text()
            )
        asyncio.run(run_pipeline(args.fixture, out_dir, decomposition=decomp))
    else:
        # Default: use golden fixture
        fixture = PROJECT_ROOT / "tests" / "fixtures" / "session_storage_bundle.json"
        out_dir = args.output_dir or (PROJECT_ROOT / "output" / "pipeline")
        asyncio.run(run_pipeline(fixture, out_dir))


if __name__ == "__main__":
    main()
