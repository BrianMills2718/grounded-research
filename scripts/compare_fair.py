"""Fair comparison: holistic quality without provenance bias.

Evaluates two reports on dimensions that all research tools are trying
to do well on, without penalizing tools that deliberately omit internal
citation IDs for readability.

Usage:
    python scripts/compare_fair.py report_a.md report_b.md [--judge MODEL]
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


FAIR_JUDGE_SYSTEM = """\
You are an expert research quality evaluator. You will compare two research
reports (Report A and Report B) that analyze the same topic. You do not know
which report was produced by which method.

Evaluate ONLY on these dimensions (1-5 scale). Do NOT evaluate citation
format, internal IDs, or provenance mechanics — different tools use different
citation styles and none is inherently better.

1. **Factual Accuracy**: Are the claims correct and specific? Are dates,
   numbers, and policy details accurate? Does the report avoid vague or
   unsupported assertions?

2. **Completeness**: Does the report cover the important aspects of the
   question? Are there significant omissions?

3. **Conflict and Nuance**: Does the report identify genuine disagreements
   or uncertainties in the evidence? Does it distinguish between what's
   well-established and what's contested? Does it avoid false confidence?

4. **Analytical Depth**: Does the report go beyond summarizing facts to
   explain WHY things happened, what the tradeoffs are, and what the
   implications are? Does it help the reader think, not just know?

5. **Decision Usefulness**: If you were a policymaker or analyst who needed
   to act on this topic, which report would better equip you to make a
   good decision? Are recommendations specific and conditional?

For each dimension, score both reports (1-5) and explain which is better
and why with specific quotes. Then give an overall verdict.

IMPORTANT: Ignore citation style entirely. A report that uses [1][2][3],
(Smith 2024), or inline IDs like (C-abc123) should be judged the same on
all dimensions. What matters is whether the claims are substantive and
well-reasoned, not how they reference sources.
"""


async def compare_fair(
    report_a_path: Path,
    report_b_path: Path,
    judge_model: str = "openrouter/openai/gpt-5-nano",
) -> None:
    """Run fair comparison without provenance bias."""
    from llm_client import acall_llm

    report_a = report_a_path.read_text()
    report_b = report_b_path.read_text()

    print(f"=== Fair Comparison (no provenance bias) ===")
    print(f"Report A: {len(report_a.split())} words")
    print(f"Report B: {len(report_b.split())} words")
    print(f"Judge: {judge_model}")
    print()

    user_msg = f"""## Report A

{report_a}

## Report B

{report_b}

## Instructions

Score both reports on all 5 dimensions (1-5 each). Ignore citation format.
Then give your overall verdict on which is more useful for a decision-maker.
"""

    messages = [
        {"role": "system", "content": FAIR_JUDGE_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    llm_result = await acall_llm(
        judge_model,
        messages,
        task="fair_comparison_judge",
        trace_id=f"fair_judge/{judge_model.split('/')[-1]}",
        max_budget=1.0,
    )

    print(llm_result.content)

    # Save
    stem_a = report_a_path.parent.name
    stem_b = report_b_path.parent.name
    out = PROJECT_ROOT / "output" / f"fair_{stem_a}_vs_{stem_b}.md"
    out.write_text(
        f"# Fair Comparison (no provenance bias)\n\n"
        f"**Judge:** {judge_model}\n"
        f"**Report A:** {report_a_path} ({len(report_a.split())} words)\n"
        f"**Report B:** {report_b_path} ({len(report_b.split())} words)\n\n"
        f"{llm_result.content}\n"
    )
    print(f"\nSaved to: {out}")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("report_a", type=Path)
    parser.add_argument("report_b", type=Path)
    parser.add_argument("--judge", default="openrouter/openai/gpt-5-nano")
    args = parser.parse_args()
    asyncio.run(compare_fair(args.report_a, args.report_b, args.judge))


if __name__ == "__main__":
    main()
