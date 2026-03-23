"""Run Stanford STORM on a research question for SOTA comparison.

Usage:
    python scripts/run_storm.py "research question" --output-dir output/storm_sanctions
"""

from __future__ import annotations

import asyncio
import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_storm(question: str, output_dir: Path) -> None:
    """Run STORM and save output."""
    from knowledge_storm import STORMWikiRunnerArguments, STORMWikiRunner, STORMWikiLMConfigs
    from knowledge_storm.lm import OpenAIModel

    output_dir.mkdir(parents=True, exist_ok=True)

    # Configure LM
    lm_configs = STORMWikiLMConfigs()
    openai_kwargs = {
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "temperature": 1.0,
        "top_p": 0.9,
    }

    # Use GPT-4o-mini for cost efficiency (STORM makes many calls)
    conv_model = OpenAIModel(model="gpt-4o-mini", max_tokens=500, **openai_kwargs)
    article_model = OpenAIModel(model="gpt-4o-mini", max_tokens=3000, **openai_kwargs)

    lm_configs.set_conv_simulator_lm(conv_model)
    lm_configs.set_question_asker_lm(conv_model)
    lm_configs.set_outline_gen_lm(article_model)
    lm_configs.set_article_gen_lm(article_model)
    lm_configs.set_article_polish_lm(article_model)

    # Configure retrieval module (Brave Search)
    from knowledge_storm.rm import BraveRM

    brave_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
    if not brave_key:
        raise RuntimeError("BRAVE_SEARCH_API_KEY not set")
    rm = BraveRM(brave_search_api_key=brave_key, k=3)

    # Configure runner
    engine_args = STORMWikiRunnerArguments(
        output_dir=str(output_dir),
        max_conv_turn=3,
        max_perspective=3,
        search_top_k=3,
    )

    # Run
    print(f"=== STORM ===")
    print(f"Question: {question}")
    print(f"Output: {output_dir}")
    print()

    runner = STORMWikiRunner(engine_args, lm_configs, rm)

    start = datetime.now(timezone.utc)
    try:
        runner.run(
            topic=question,
            do_research=True,
            do_generate_outline=True,
            do_generate_article=True,
            do_polish_article=True,
        )
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        print(f"Completed in {elapsed:.1f}s")

        # Save metadata
        meta = {
            "tool": "STORM",
            "question": question,
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        (output_dir / "storm_meta.json").write_text(json.dumps(meta, indent=2))

    except Exception as e:
        print(f"STORM failed: {e}")
        (output_dir / "storm_error.txt").write_text(str(e))
        raise


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("question", type=str)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "output" / "storm")
    args = parser.parse_args()
    run_storm(args.question, args.output_dir)


if __name__ == "__main__":
    main()
