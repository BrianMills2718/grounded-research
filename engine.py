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

        # --- Phase 2: Analyze ---
        phase_start = datetime.now(timezone.utc)
        state.current_phase = "analyze"
        print("\n[Phase 2] Running 3 independent analysts...")

        analyst_runs = await run_analysts(bundle, trace_id)
        state.analyst_runs = analyst_runs

        succeeded = [r for r in analyst_runs if r.succeeded]
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

        raw_claims, claim_to_analyst = extract_raw_claims(analyst_runs)
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
        )
        print(f"  Long report: {len(long_report_md)} chars, ~{len(long_report_md.split())} words")

        state.phase_traces[-1].llm_calls = 2  # structured + long-form
        state.phase_traces[-1].output_summary = (
            f"Structured report: {len(report.cited_claim_ids)} cited claims, "
            f"{len(grounding_errors)} grounding warnings. "
            f"Long report: ~{len(long_report_md.split())} words."
        )

        # Write outputs
        paths = write_outputs(state, output_dir, long_report_md=long_report_md)
        for name, path in paths.items():
            print(f"  Wrote: {path}")

        state.current_phase = "complete"
        state.success = True
        state.completed_at = datetime.now(timezone.utc)

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

    run_id = uuid.uuid4().hex[:12]
    trace_id = f"pipeline/{run_id}"

    print(f"=== Evidence Collection ===")
    print(f"Question: {question}")
    print()

    bundle = await collect_evidence(question, trace_id)

    # Save the collected bundle for reuse
    bundle_path = output_dir / "collected_bundle.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(bundle.model_dump_json(indent=2))
    print(f"  Saved bundle: {bundle_path}")
    print()

    return await run_pipeline(bundle_path, output_dir)


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
    args = parser.parse_args()

    if args.question:
        slug = args.question[:40].lower().replace(" ", "_").replace("?", "")
        out_dir = args.output_dir or (PROJECT_ROOT / "output" / slug)
        asyncio.run(run_pipeline_from_question(args.question, out_dir))
    elif args.fixture:
        out_dir = args.output_dir or (PROJECT_ROOT / "output" / "pipeline")
        asyncio.run(run_pipeline(args.fixture, out_dir))
    else:
        # Default: use golden fixture
        fixture = PROJECT_ROOT / "tests" / "fixtures" / "session_storage_bundle.json"
        out_dir = args.output_dir or (PROJECT_ROOT / "output" / "pipeline")
        asyncio.run(run_pipeline(fixture, out_dir))


if __name__ == "__main__":
    main()
