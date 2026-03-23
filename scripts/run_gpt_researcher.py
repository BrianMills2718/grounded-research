"""Run GPT-Researcher on a research question for SOTA comparison.

Usage:
    python scripts/run_gpt_researcher.py "research question" --output-dir output/gptr_sanctions
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


async def run_gpt_researcher(question: str, output_dir: Path) -> None:
    """Run GPT-Researcher and save output."""
    from gpt_researcher import GPTResearcher

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== GPT-Researcher ===")
    print(f"Question: {question}")
    print(f"Output: {output_dir}")
    print()

    start = datetime.now(timezone.utc)

    researcher = GPTResearcher(query=question, report_type="research_report")
    research_result = await researcher.conduct_research()
    report = await researcher.write_report()

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()

    # Save report
    report_path = output_dir / "gpt_researcher_report.md"
    report_path.write_text(report)

    # Save metadata
    meta = {
        "tool": "GPT-Researcher",
        "question": question,
        "elapsed_seconds": elapsed,
        "report_length_chars": len(report),
        "report_length_words": len(report.split()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / "gpt_researcher_meta.json").write_text(json.dumps(meta, indent=2))

    print(f"Report: {len(report)} chars, ~{len(report.split())} words")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Wrote: {report_path}")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("question", type=str)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "output" / "gpt_researcher")
    args = parser.parse_args()
    asyncio.run(run_gpt_researcher(args.question, args.output_dir))


if __name__ == "__main__":
    main()
