#!/usr/bin/env python3
"""Migrate one legacy saved fixture into Tyler-compatible fixture artifacts.

This script exists for frozen-eval and migration work only. It does not reopen
legacy runtime contracts inside the live pipeline. Instead, it converts:

- `decomposition.json` -> `tyler_stage_1.json`
- legacy `sub_question_id` / `SQ-*` evidence tags -> Tyler `Q-*` tags

so current Tyler-native runs can consume archived saved bundles reproducibly.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from grounded_research.models import EvidenceBundle
from grounded_research.tyler_v1_models import (
    DecompositionResult,
    ResearchPlan,
    StageSummary,
    SubQuestion,
)


def _map_legacy_sub_question_type(legacy_type: str) -> str:
    """Map legacy decomposition types into Tyler's Stage 1 type enum."""

    normalized = legacy_type.strip().lower()
    if normalized in {"factual", "empirical"}:
        return "empirical"
    if normalized in {"preference", "normative"}:
        return "preference"
    return "interpretive"


def _default_research_priority(mapped_type: str, position: int) -> str:
    """Choose a deterministic priority for migrated legacy sub-questions."""

    if mapped_type == "empirical":
        return "high"
    if mapped_type == "preference":
        return "low"
    return "high" if position == 1 else "medium"


def migrate_legacy_decomposition(raw: dict[str, Any]) -> tuple[DecompositionResult, dict[str, str]]:
    """Convert one legacy `decomposition.json` payload into Tyler Stage 1."""

    legacy_sub_questions = list(raw.get("sub_questions") or [])
    if len(legacy_sub_questions) < 2:
        raise ValueError("Legacy decomposition must contain at least two sub-questions.")

    id_map: dict[str, str] = {}
    sub_questions: list[SubQuestion] = []
    falsification_targets: list[str] = []
    for idx, item in enumerate(legacy_sub_questions, start=1):
        legacy_id = str(item.get("id", "")).strip()
        if not legacy_id:
            raise ValueError("Legacy decomposition sub-question is missing an id.")
        question_text = str(item.get("text", "")).strip()
        if not question_text:
            raise ValueError(f"Legacy decomposition sub-question {legacy_id!r} is missing text.")
        tyler_id = f"Q-{idx}"
        mapped_type = _map_legacy_sub_question_type(str(item.get("type", "")))
        id_map[legacy_id] = tyler_id
        falsification_target = str(item.get("falsification_target", "")).strip() or "No explicit falsification target recorded in the legacy fixture."
        falsification_targets.append(falsification_target)
        sub_questions.append(
            SubQuestion(
                id=tyler_id,
                question=question_text,
                type=mapped_type,
                research_priority=_default_research_priority(mapped_type, idx),
                search_guidance=f"Gather sources that directly answer: {question_text}",
            )
        )

    stage_1 = DecompositionResult(
        core_question=str(raw.get("core_question", "")).strip(),
        sub_questions=sub_questions,
        optimization_axes=[str(axis) for axis in raw.get("optimization_axes", []) if str(axis).strip()],
        research_plan=ResearchPlan(
            what_to_verify=[sub_question.question for sub_question in sub_questions],
            critical_source_types=["official docs", "academic studies", "practitioner reports"],
            falsification_targets=falsification_targets,
        ),
        stage_summary=StageSummary(
            stage_name="Stage 1: Decomposition",
            goal="Migrate a legacy saved fixture into Tyler Stage 1 form for frozen evaluation.",
            key_findings=[
                f"Migrated {len(sub_questions)} legacy sub-questions into Tyler Q-ids.",
                "Preserved the archived fixture question and falsification targets.",
            ],
            decisions_made=[
                "Mapped factual/empirical legacy types to Tyler empirical.",
                "Mapped evaluative and other non-preference legacy types to Tyler interpretive.",
            ],
            outcome=f"Tyler-compatible Stage 1 fixture with {len(sub_questions)} sub-questions",
            reasoning="This migration exists only to make archived fixtures consumable by the Tyler-native runtime.",
        ),
    )
    return stage_1, id_map


def migrate_legacy_bundle(raw_bundle: dict[str, Any], *, id_map: dict[str, str]) -> EvidenceBundle:
    """Rewrite legacy evidence tags into Tyler Stage 1 `Q-*` ids."""

    evidence_rows = list(raw_bundle.get("evidence") or [])
    normalized_evidence: list[dict[str, Any]] = []
    for item in evidence_rows:
        upgraded = dict(item)
        sub_question_ids = upgraded.get("sub_question_ids")
        if sub_question_ids is None:
            legacy_single = upgraded.pop("sub_question_id", None)
            sub_question_ids = [legacy_single] if legacy_single else []
        normalized_ids: list[str] = []
        for sub_question_id in sub_question_ids:
            if sub_question_id in id_map:
                normalized_ids.append(id_map[sub_question_id])
            elif str(sub_question_id).startswith("Q-"):
                normalized_ids.append(str(sub_question_id))
            else:
                raise ValueError(
                    "Legacy fixture bundle references unknown sub-question id "
                    f"{sub_question_id!r}; known ids: {sorted(id_map)}"
                )
        upgraded["sub_question_ids"] = normalized_ids
        normalized_evidence.append(upgraded)

    normalized_raw = dict(raw_bundle)
    normalized_raw["evidence"] = normalized_evidence
    imported_from = str(normalized_raw.get("imported_from", "manual")).strip() or "manual"
    normalized_raw["imported_from"] = f"{imported_from}+legacy_tyler_fixture_migration"
    return EvidenceBundle.model_validate(normalized_raw)


def parse_args() -> argparse.Namespace:
    """Parse CLI args for fixture migration."""

    parser = argparse.ArgumentParser(description="Migrate one legacy saved fixture into Tyler-compatible artifacts.")
    parser.add_argument("--bundle", required=True, help="Path to legacy collected_bundle.json")
    parser.add_argument("--decomposition", required=True, help="Path to sibling legacy decomposition.json")
    parser.add_argument("--output-dir", required=True, help="Directory where migrated fixture_bundle.json and tyler_stage_1.json are written")
    return parser.parse_args()


def main() -> None:
    """Run the one-shot legacy fixture migration."""

    args = parse_args()
    bundle_path = Path(args.bundle).expanduser().resolve()
    decomposition_path = Path(args.decomposition).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    legacy_decomposition = json.loads(decomposition_path.read_text())
    legacy_bundle = json.loads(bundle_path.read_text())

    stage_1, id_map = migrate_legacy_decomposition(legacy_decomposition)
    bundle = migrate_legacy_bundle(legacy_bundle, id_map=id_map)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "tyler_stage_1.json").write_text(stage_1.model_dump_json(indent=2) + "\n")
    (output_dir / "fixture_bundle.json").write_text(bundle.model_dump_json(indent=2) + "\n")
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "fixture_bundle": str(output_dir / "fixture_bundle.json"),
                "tyler_stage_1": str(output_dir / "tyler_stage_1.json"),
                "sub_questions": len(stage_1.sub_questions),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
