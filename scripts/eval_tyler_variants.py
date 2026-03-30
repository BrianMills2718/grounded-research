"""Evaluate frozen Tyler-literal versus archived legacy outputs via prompt_eval.

This script keeps `grounded-research` on one canonical runtime path. It scores
saved artifacts through `prompt_eval` rather than reviving a second runtime
mode inside this repo.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = PROJECT_ROOT / "config" / "eval_manifests" / "tyler_literal_default_eval_wave1.json"


class FrozenArtifact(BaseModel):
    """One hashed frozen artifact used in a saved-outputs comparison."""

    path: str = Field(description="Repo-relative path to the frozen file.")
    sha256: str = Field(description="Expected SHA-256 hash for the frozen file.")


class FrozenVariant(BaseModel):
    """One historical variant in a frozen comparison manifest."""

    name: str = Field(description="Short internal variant key.")
    label: str = Field(description="Human-readable variant label.")
    commit_anchor: str = Field(description="Commit hash used to recover this historical variant.")
    artifact_dir: str = Field(description="Repo-relative output directory holding the saved artifacts.")
    files: dict[str, FrozenArtifact] = Field(description="Named frozen files for this variant.")


class FrozenComparisonManifest(BaseModel):
    """Manifest for one saved-output comparison wave."""

    experiment_name: str = Field(description="Stable experiment name for prompt_eval and outputs.")
    question: str = Field(description="The shared user question behind all saved artifacts.")
    variants: list[FrozenVariant] = Field(description="Variants included in this frozen comparison.")


def _sha256(path: Path) -> str:
    """Return the SHA-256 hash for one file path."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(path: Path = DEFAULT_MANIFEST) -> FrozenComparisonManifest:
    """Load one frozen comparison manifest from disk."""
    return FrozenComparisonManifest.model_validate_json(path.read_text())


def verify_manifest(manifest: FrozenComparisonManifest) -> None:
    """Fail loudly when a frozen manifest does not match the files on disk."""
    if len(manifest.variants) < 2:
        raise ValueError("Frozen comparison manifest must include at least two variants.")
    if not manifest.question.strip():
        raise ValueError("Frozen comparison manifest question must be non-empty.")
    variant_names = {variant.name for variant in manifest.variants}
    if len(variant_names) != len(manifest.variants):
        raise ValueError("Frozen comparison manifest contains duplicate variant names.")

    for variant in manifest.variants:
        for artifact in variant.files.values():
            artifact_path = PROJECT_ROOT / artifact.path
            if not artifact_path.exists():
                raise ValueError(f"Frozen artifact missing on disk: {artifact.path}")
            actual_hash = _sha256(artifact_path)
            if actual_hash != artifact.sha256:
                raise ValueError(
                    f"Frozen artifact hash mismatch for {artifact.path}: "
                    f"expected {artifact.sha256}, got {actual_hash}"
                )


def build_precomputed_payloads(
    manifest: FrozenComparisonManifest,
    *,
    repeats: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build plain-Python inputs and outputs for prompt_eval precomputed scoring."""
    input_id = manifest.experiment_name
    inputs = [
        {
            "id": input_id,
            "content": manifest.question,
            "expected": manifest.question,
        }
    ]
    outputs: list[dict[str, Any]] = []
    for variant in manifest.variants:
        report_artifact = variant.files["report_md"]
        report_path = PROJECT_ROOT / report_artifact.path
        report_text = report_path.read_text()
        for replicate in range(repeats):
            outputs.append(
                {
                    "variant_name": variant.name,
                    "input_id": input_id,
                    "output": report_text,
                    "replicate": replicate,
                    "provenance": {
                        "artifact_dir": variant.artifact_dir,
                        "report_path": report_artifact.path,
                        "report_sha256": report_artifact.sha256,
                        "commit_anchor": variant.commit_anchor,
                    },
                }
            )
    return inputs, outputs


def _configure_eval_runtime(output_dir: Path) -> None:
    """Apply a run-local observability DB for eval-time judge calls."""
    os.environ["LLM_CLIENT_TIMEOUT_POLICY"] = "allow"
    os.environ["LLM_CLIENT_DB_PATH"] = str(output_dir / "llm_observability.db")


def _quality_dimensions():
    """Return the shared evaluation rubric dimensions."""
    try:
        from prompt_eval import RubricDimension
    except ImportError as exc:  # pragma: no cover - live dependency surface
        raise RuntimeError(
            "prompt_eval must be installed in this environment. "
            "Install the clean worktree branch before running this script."
        ) from exc

    return [
        RubricDimension(
            name="factual_accuracy",
            description=(
                "Judge whether the report makes specific, credible, non-vague "
                "claims and avoids unsupported assertions."
            ),
        ),
        RubricDimension(
            name="completeness",
            description=(
                "Judge whether the report covers the important aspects of the "
                "question without major omissions."
            ),
        ),
        RubricDimension(
            name="conflict_and_nuance",
            description=(
                "Judge whether the report distinguishes contested points from "
                "well-established ones and surfaces real uncertainty."
            ),
        ),
        RubricDimension(
            name="analytical_depth",
            description=(
                "Judge whether the report explains mechanisms, tradeoffs, and "
                "implications rather than only summarizing facts."
            ),
        ),
        RubricDimension(
            name="decision_usefulness",
            description=(
                "Judge whether the report would better equip a policymaker or "
                "analyst to make a decision, including specific conditional guidance."
            ),
        ),
    ]


def _build_evaluator(judge_model: str):
    """Create the dimensional evaluator for saved report text."""
    try:
        from prompt_eval import llm_judge_dimensional_evaluator
    except ImportError as exc:  # pragma: no cover - live dependency surface
        raise RuntimeError(
            "prompt_eval must be installed in this environment. "
            "Install the clean worktree branch before running this script."
        ) from exc

    base = llm_judge_dimensional_evaluator(
        _quality_dimensions(),
        judge_models=[judge_model],
    )

    async def evaluate(output: Any, expected: Any = None):
        question = str(expected or "").strip()
        wrapped_output = f"Question:\n{question}\n\nReport:\n{output}"
        return await base(wrapped_output, None)

    return evaluate


async def run_frozen_eval(
    *,
    manifest_path: Path,
    output_dir: Path,
    repeats: int,
    judge_model: str,
) -> Path:
    """Run the saved-artifact comparison and write result files."""
    try:
        from prompt_eval import (
            ExperimentInput,
            PrecomputedOutput,
            PromptEvalObservabilityConfig,
            compare_variants,
            evaluate_precomputed_variants,
        )
    except ImportError as exc:  # pragma: no cover - live dependency surface
        raise RuntimeError(
            "prompt_eval must be installed in this environment. "
            "Install the clean worktree branch before running this script."
        ) from exc

    manifest = load_manifest(manifest_path)
    verify_manifest(manifest)
    inputs_data, outputs_data = build_precomputed_payloads(manifest, repeats=repeats)
    inputs = [ExperimentInput(**item) for item in inputs_data]
    outputs = [PrecomputedOutput(**item) for item in outputs_data]

    output_dir.mkdir(parents=True, exist_ok=True)
    _configure_eval_runtime(output_dir)

    result = await evaluate_precomputed_variants(
        experiment_name=manifest.experiment_name,
        inputs=inputs,
        outputs=outputs,
        evaluator=_build_evaluator(judge_model),
        observability=PromptEvalObservabilityConfig(
            project="grounded_research",
            dataset=manifest.experiment_name,
        ),
    )
    comparison = compare_variants(
        result,
        "tyler_literal",
        "calibrated_legacy",
        comparison_mode="pooled",
        method="bootstrap",
    )

    result_path = output_dir / "result.json"
    result_path.write_text(result.model_dump_json(indent=2))
    summary_path = output_dir / "summary.md"
    summary_path.write_text(_render_summary(manifest, result, comparison, judge_model, repeats))
    return summary_path


def _render_summary(
    manifest: FrozenComparisonManifest,
    result,
    comparison,
    judge_model: str,
    repeats: int,
) -> str:
    """Render a compact Markdown summary for the frozen comparison run."""
    lines = [
        f"# {manifest.experiment_name}",
        "",
        f"**Judge model:** `{judge_model}`",
        f"**Replicates per variant:** {repeats}",
        f"**Question:** {manifest.question}",
        "",
        "## Variant Means",
        "",
    ]
    for variant_name in result.variants:
        summary = result.summary[variant_name]
        lines.append(f"### {variant_name}")
        lines.append(f"- mean score: `{summary.mean_score}`")
        lines.append(f"- trials: `{summary.n_trials}`")
        lines.append(f"- errors: `{summary.n_errors}`")
        if summary.dimension_means:
            for dim_name, dim_score in sorted(summary.dimension_means.items()):
                lines.append(f"- {dim_name}: `{dim_score}`")
        lines.append("")

    lines.extend(
        [
            "## Comparison",
            "",
            f"- mean tyler_literal: `{comparison.mean_a}`",
            f"- mean calibrated_legacy: `{comparison.mean_b}`",
            f"- difference: `{comparison.difference}`",
            f"- confidence interval: `[{comparison.ci_lower}, {comparison.ci_upper}]`",
            f"- significant: `{comparison.significant}`",
            f"- detail: {comparison.detail}",
            "",
            "## Limits",
            "",
            "- one shared benchmark case only",
            "- judge replicates estimate scoring noise but do not create broad task coverage",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI entrypoint for frozen Tyler-variant evaluation."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to the frozen comparison manifest JSON.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "output" / "tyler_literal_default_eval_wave1",
        help="Directory for eval outputs.",
    )
    parser.add_argument(
        "--judge-model",
        default="openrouter/openai/gpt-5.4-mini",
        help="Judge model for prompt_eval dimensional scoring.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Number of repeated judge-scoring trials per frozen variant.",
    )
    args = parser.parse_args()
    summary_path = asyncio.run(
        run_frozen_eval(
            manifest_path=args.manifest,
            output_dir=args.output_dir,
            repeats=args.repeats,
            judge_model=args.judge_model,
        )
    )
    print(f"Saved summary to: {summary_path}")


if __name__ == "__main__":
    main()
