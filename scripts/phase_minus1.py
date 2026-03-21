"""Phase -1: Thesis Falsification.

Runs 3 cross-family models on the same evidence bundle and produces
analyst outputs for manual disagreement review.

Usage:
    python scripts/phase_minus1.py [--fixture PATH] [--output-dir PATH]
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from grounded_research.models import (
    AnalystRun,
    Assumption,
    Counterargument,
    EvidenceBundle,
    EvidenceItem,
    RawClaim,
    Recommendation,
    ResearchQuestion,
    SourceRecord,
)


def load_config() -> dict:
    """Load project config."""
    config_path = PROJECT_ROOT / "config" / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_fixture(path: Path) -> EvidenceBundle:
    """Load a JSON evidence bundle into typed models."""
    raw = json.loads(path.read_text())
    question = ResearchQuestion(**raw["question"])
    sources = [SourceRecord(**s) for s in raw["sources"]]
    evidence = [EvidenceItem(**e) for e in raw["evidence"]]
    return EvidenceBundle(
        question=question,
        sources=sources,
        evidence=evidence,
        gaps=raw.get("gaps", []),
        imported_from=raw.get("imported_from", "manual"),
    )


def render_analyst_prompt(bundle: EvidenceBundle, frame: str) -> list[dict[str, str]]:
    """Render the analyst prompt template with evidence."""
    from llm_client import render_prompt

    return render_prompt(
        str(PROJECT_ROOT / "prompts" / "analyst.yaml"),
        question=bundle.question.model_dump(),
        evidence=[e.model_dump() for e in bundle.evidence],
        frame=frame,
    )


async def run_single_analyst(
    model: str,
    label: str,
    bundle: EvidenceBundle,
    frame: str,
    trace_id: str,
    max_budget: float,
) -> AnalystRun:
    """Run one analyst and return the result."""
    from llm_client import acall_llm_structured

    messages = render_analyst_prompt(bundle, frame)

    try:
        result, meta = await acall_llm_structured(
            model,
            messages,
            response_model=AnalystRun,
            task="analyst_reasoning",
            trace_id=f"{trace_id}/{label}",
            max_budget=max_budget,
        )
        # Fill in metadata that the LLM doesn't set
        result.analyst_label = label
        result.model = model
        result.frame = frame
        result.completed_at = datetime.now(timezone.utc)
        return result
    except Exception as e:
        return AnalystRun(
            analyst_label=label,
            model=model,
            frame=frame,
            error=str(e),
            completed_at=datetime.now(timezone.utc),
        )


async def run_phase_minus1(
    fixture_path: Path,
    output_dir: Path,
) -> None:
    """Run the full Phase -1 thesis falsification."""
    config = load_config()
    models = config["phase_minus1_models"]
    labels = ["Alpha", "Beta", "Gamma"]
    frame = "general"
    trace_id = f"phase-1/{uuid.uuid4().hex[:8]}"
    max_budget = config["budgets"]["pipeline_max_budget_usd"] / 3

    print(f"=== Phase -1: Thesis Falsification ===")
    print(f"Trace ID: {trace_id}")
    print(f"Models: {models}")
    print(f"Budget per analyst: ${max_budget:.2f}")
    print()

    # Load evidence
    bundle = load_fixture(fixture_path)
    print(f"Question: {bundle.question.text}")
    print(f"Evidence items: {len(bundle.evidence)}")
    print(f"Sources: {len(bundle.sources)}")
    print()

    # Run 3 analysts in parallel
    print("Running 3 analysts in parallel...")
    tasks = [
        run_single_analyst(model, label, bundle, frame, trace_id, max_budget)
        for model, label in zip(models, labels)
    ]
    results = await asyncio.gather(*tasks)

    # Check success
    succeeded = [r for r in results if r.succeeded]
    failed = [r for r in results if not r.succeeded]

    print(f"\nResults: {len(succeeded)} succeeded, {len(failed)} failed")
    for r in failed:
        print(f"  FAILED [{r.analyst_label}] ({r.model}): {r.error}")
    print()

    # Write output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Individual analyst outputs
    for r in results:
        path = output_dir / f"analyst_{r.analyst_label.lower()}.json"
        path.write_text(r.model_dump_json(indent=2))
        print(f"Wrote: {path}")

    # Summary for manual review
    summary = {
        "trace_id": trace_id,
        "question": bundle.question.text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "models": models,
        "analysts": [],
    }

    for r in results:
        analyst_summary = {
            "label": r.analyst_label,
            "model": r.model,
            "succeeded": r.succeeded,
            "error": r.error,
            "claim_count": len(r.claims),
            "assumption_count": len(r.assumptions),
            "recommendation_count": len(r.recommendations),
            "counterargument_count": len(r.counterarguments),
            "claims": [
                {"id": c.id, "statement": c.statement, "confidence": c.confidence}
                for c in r.claims
            ],
            "recommendations": [
                {"statement": rec.statement, "conditions": rec.conditions}
                for rec in r.recommendations
            ],
        }
        summary["analysts"].append(analyst_summary)

    # Disagreement analysis (manual review scaffold)
    if len(succeeded) >= 2:
        pairs = []
        for i, a in enumerate(succeeded):
            for b in succeeded[i + 1 :]:
                pair = {
                    "pair": f"{a.analyst_label}-{b.analyst_label}",
                    "models": f"{a.model} vs {b.model}",
                    "a_recommendation": (
                        a.recommendations[0].statement if a.recommendations else "(none)"
                    ),
                    "b_recommendation": (
                        b.recommendations[0].statement if b.recommendations else "(none)"
                    ),
                    "a_claim_count": len(a.claims),
                    "b_claim_count": len(b.claims),
                    # Manual review fields — fill these in
                    "substantive_disagreement": None,
                    "decision_relevant": None,
                    "evidence_grounded": None,
                    "resolvable": None,
                }
                pairs.append(pair)
        summary["disagreement_pairs"] = pairs
        summary["review_rubric"] = {
            "substantive_disagreement": "Do analysts reach different conclusions? (yes/no)",
            "decision_relevant": "Would it change what a team does? (yes/no/marginal)",
            "evidence_grounded": "Different evidence or just different framing? (different_evidence/different_framing/both)",
            "resolvable": "Could new evidence resolve it? (yes/no/unclear)",
            "pass_threshold": "At least 2 of 3 pairs show substantive, decision-relevant disagreement",
        }

    summary_path = output_dir / "phase_minus1_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"Wrote: {summary_path}")

    # Print quick review
    print("\n=== Quick Review ===")
    for r in succeeded:
        print(f"\n--- {r.analyst_label} ({r.model}) ---")
        if r.recommendations:
            print(f"  Recommendation: {r.recommendations[0].statement[:100]}...")
        print(f"  Claims: {len(r.claims)}")
        for c in r.claims[:3]:
            print(f"    [{c.confidence}] {c.statement[:80]}...")

    if "disagreement_pairs" in summary:
        print("\n=== Disagreement Pairs (fill in manually) ===")
        for pair in summary["disagreement_pairs"]:
            print(f"\n  {pair['pair']} ({pair['models']})")
            print(f"    A: {pair['a_recommendation'][:80]}...")
            print(f"    B: {pair['b_recommendation'][:80]}...")

    print(f"\n=== Next: Review {summary_path} and fill in rubric scores ===")


def main() -> None:
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Phase -1: Thesis Falsification")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=PROJECT_ROOT / "tests" / "fixtures" / "session_storage_bundle.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "output" / "phase_minus1",
    )
    args = parser.parse_args()

    asyncio.run(run_phase_minus1(args.fixture, args.output_dir))


if __name__ == "__main__":
    main()
