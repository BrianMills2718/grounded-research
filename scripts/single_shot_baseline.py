"""Single-shot baseline for controlled comparison.

Sends the same evidence bundle to a single strong LLM call and asks for a
grounded assessment. Compares against the full pipeline output to measure
whether the multi-analyst adjudication pipeline adds value.

Usage:
    python scripts/single_shot_baseline.py output/pfas_health_risks/collected_bundle.json
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


SINGLE_SHOT_SYSTEM = """\
You are a research analyst producing a grounded assessment of evidence.

Your job is to:
1. Read all evidence carefully
2. Form claims supported by specific evidence items (cite evidence IDs like E-...)
3. Identify areas of disagreement or ambiguity in the evidence
4. Surface assumptions
5. Make recommendations with conditions
6. Note evidence gaps

Be specific. Cite evidence IDs for every claim. Do not invent information
beyond what the evidence contains. If evidence conflicts, explicitly state
the conflict and which sources disagree.

Produce a structured report with sections:
- Key Claims (with evidence citations)
- Disagreements and Conflicts Found
- Evidence Gaps
- Recommendations
- Conditions That Would Change These Recommendations
"""


async def run_single_shot(bundle_path: Path, output_dir: Path) -> None:
    """Run single-shot synthesis on the same evidence bundle."""
    from llm_client import acall_llm

    with open(bundle_path) as f:
        bundle = json.load(f)

    # Build evidence text (same format as pipeline analysts see)
    evidence_text = []
    for item in bundle["evidence"]:
        line = f"### {item['id']} (from {item['source_id']})\n"
        line += f"Type: {item.get('content_type', 'text')}\n"
        line += item["content"]
        if item.get("relevance_note"):
            line += f"\nRelevance: {item['relevance_note']}"
        evidence_text.append(line)

    user_msg = f"""## Research Question

{bundle['question']['text']}

Time sensitivity: {bundle['question'].get('time_sensitivity', 'mixed')}

## Evidence

{chr(10).join(evidence_text)}

## Instructions

Analyze the evidence above and produce your grounded assessment.
For each claim, cite the evidence IDs that support it.
Explicitly flag any conflicts between sources.
"""

    messages = [
        {"role": "system", "content": SINGLE_SHOT_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    # Use the strongest available model for a fair comparison
    model = "gemini/gemini-2.5-flash"

    print(f"=== Single-Shot Baseline ===")
    print(f"Model: {model}")
    print(f"Evidence items: {len(bundle['evidence'])}")
    print(f"Sources: {len(bundle['sources'])}")
    print()

    start = datetime.now(timezone.utc)
    llm_result = await acall_llm(
        model,
        messages,
        task="single_shot_baseline",
        trace_id="baseline/single_shot",
        max_budget=1.0,
    )
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    result = llm_result.content

    # Write output
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "single_shot_report.md"
    report_path.write_text(result)

    meta_path = output_dir / "single_shot_meta.json"
    meta_path.write_text(json.dumps({
        "model": model,
        "elapsed_seconds": elapsed,
        "evidence_count": len(bundle["evidence"]),
        "source_count": len(bundle["sources"]),
        "report_length_chars": len(result),
        "report_length_words": len(result.split()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, indent=2))

    print(f"Report: {len(result)} chars, ~{len(result.split())} words")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Wrote: {report_path}")
    print(f"Wrote: {meta_path}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Single-shot baseline comparison")
    parser.add_argument("bundle", type=Path, help="Path to evidence bundle JSON")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    out_dir = args.output_dir or (PROJECT_ROOT / "output" / "baseline")
    asyncio.run(run_single_shot(args.bundle, out_dir))


if __name__ == "__main__":
    main()
