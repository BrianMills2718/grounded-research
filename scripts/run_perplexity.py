"""Run Perplexity Deep Research on a question for SOTA comparison.

Perplexity's API is OpenAI-compatible. Uses the sonar-deep-research model
for maximum quality comparison.

Usage:
    python scripts/run_perplexity.py "research question" --output-dir output/perplexity_sanctions
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


async def run_perplexity(question: str, output_dir: Path) -> None:
    """Run Perplexity and save output."""
    from openai import AsyncOpenAI

    api_key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY not set")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.perplexity.ai",
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Perplexity ===")
    print(f"Question: {question}")
    print(f"Output: {output_dir}")
    print()

    start = datetime.now(timezone.utc)

    model = os.environ.get("PERPLEXITY_MODEL", "sonar-pro")
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a research analyst. Provide a thorough, well-sourced "
                    "analysis. Cite specific sources for every major claim. Identify "
                    "disagreements in the evidence. Note evidence gaps."
                ),
            },
            {"role": "user", "content": question},
        ],
    )

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    report = response.choices[0].message.content

    # Extract citations if available
    citations = []
    if hasattr(response, "citations") and response.citations:
        citations = response.citations

    # Save report
    report_path = output_dir / "perplexity_report.md"
    report_path.write_text(report)

    # Save metadata
    meta = {
        "tool": "Perplexity",
        "model": model,
        "question": question,
        "elapsed_seconds": elapsed,
        "report_length_chars": len(report),
        "report_length_words": len(report.split()),
        "citations_count": len(citations),
        "citations": citations,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / "perplexity_meta.json").write_text(json.dumps(meta, indent=2))

    print(f"Report: {len(report)} chars, ~{len(report.split())} words")
    print(f"Citations: {len(citations)}")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Wrote: {report_path}")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("question", type=str)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "output" / "perplexity")
    args = parser.parse_args()
    asyncio.run(run_perplexity(args.question, args.output_dir))


if __name__ == "__main__":
    main()
