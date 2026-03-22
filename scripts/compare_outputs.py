"""Compare pipeline vs single-shot baseline outputs.

Extracts key metrics and calls an LLM to do blind evaluation.

Usage:
    python scripts/compare_outputs.py \
        output/pfas_health_risks/summary.md \
        output/pfas_baseline/single_shot_report.md
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


JUDGE_SYSTEM = """\
You are an expert research quality evaluator. You will compare two research
reports (Report A and Report B) that analyze the same evidence about the same
question. You do not know which report was produced by which method.

Score each report on these dimensions (1-5 scale):

1. **Factual Precision**: Are claims specific and accurately grounded in evidence?
   Do claims cite specific evidence? Are there over-generalizations?

2. **Conflict Detection**: Does the report identify genuine disagreements,
   contradictions, or ambiguities in the evidence? Does it distinguish factual
   conflicts from interpretive differences?

3. **Evidence Coverage**: Does the report address the full breadth of the evidence,
   or does it focus narrowly? Are important evidence items missed?

4. **Nuance and Caveats**: Does the report appropriately qualify claims, note
   uncertainty, and distinguish strong from weak evidence?

5. **Actionability**: Would a decision-maker find this report useful? Are
   recommendations specific and conditional?

6. **Provenance Quality**: Can a reader trace each claim back to specific evidence?
   Is the citation trail clear and complete?

For each dimension, score both reports and explain which is better and why.
Then give an overall verdict: which report is more useful for a decision-maker
who needs to understand PFAS health risks and regulatory limits?

Be specific. Quote from the reports to support your judgments.
"""


async def compare(report_a_path: Path, report_b_path: Path) -> None:
    from llm_client import acall_llm

    report_a = report_a_path.read_text()
    report_b = report_b_path.read_text()

    # Count evidence citations in each
    a_citations = set(re.findall(r'[ECR]-[a-f0-9]{6,}', report_a))
    b_citations = set(re.findall(r'[ECR]-[a-f0-9]{6,}', report_b))

    print(f"=== Structural Metrics ===")
    print(f"Report A: {len(report_a.split())} words, {len(a_citations)} unique citations")
    print(f"Report B: {len(report_b.split())} words, {len(b_citations)} unique citations")
    print(f"Shared citations: {len(a_citations & b_citations)}")
    print(f"Only in A: {len(a_citations - b_citations)}")
    print(f"Only in B: {len(b_citations - a_citations)}")
    print()

    user_msg = f"""## Research Question

What are the documented health risks of PFAS (forever chemicals) in drinking
water, and at what concentration levels do regulatory agencies set limits?

## Report A

{report_a}

## Report B

{report_b}

## Instructions

Score both reports on all 6 dimensions (1-5 each). Then give your overall verdict.
"""

    messages = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    print("=== LLM Judge Evaluation ===")
    print("(Using gemini-2.5-flash as judge)")
    print()

    llm_result = await acall_llm(
        "gemini/gemini-2.5-flash",
        messages,
        task="baseline_comparison_judge",
        trace_id="baseline/judge",
        max_budget=1.0,
    )

    print(llm_result.content)

    # Save
    out_path = PROJECT_ROOT / "output" / "pfas_comparison.md"
    out_path.write_text(
        f"# Pipeline vs Single-Shot Comparison\n\n"
        f"## Structural Metrics\n\n"
        f"- Report A (pipeline): {len(report_a.split())} words, {len(a_citations)} unique citations\n"
        f"- Report B (single-shot): {len(report_b.split())} words, {len(b_citations)} unique citations\n"
        f"- Shared: {len(a_citations & b_citations)}, Only A: {len(a_citations - b_citations)}, Only B: {len(b_citations - a_citations)}\n\n"
        f"## Judge Evaluation\n\n{llm_result.content}\n"
    )
    print(f"\nSaved to: {out_path}")


def main() -> None:
    report_a = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_ROOT / "output" / "pfas_health_risks" / "summary.md"
    report_b = Path(sys.argv[2]) if len(sys.argv) > 2 else PROJECT_ROOT / "output" / "pfas_baseline" / "single_shot_report.md"
    asyncio.run(compare(report_a, report_b))


if __name__ == "__main__":
    main()
