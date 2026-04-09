"""Tests for legacy frozen-fixture migration into Tyler-native artifacts."""

from __future__ import annotations

import json

from scripts.migrate_legacy_fixture_to_tyler import (
    migrate_legacy_bundle,
    migrate_legacy_decomposition,
)


def test_migrate_legacy_decomposition_rewrites_ids_and_types() -> None:
    """Legacy decomposition fixtures should become deterministic Tyler Stage 1 artifacts."""

    stage_1, id_map = migrate_legacy_decomposition(
        {
            "core_question": "What happened?",
            "sub_questions": [
                {
                    "id": "SQ-a",
                    "text": "What do the benchmarks show?",
                    "type": "factual",
                    "falsification_target": "contradictory benchmark",
                },
                {
                    "id": "SQ-b",
                    "text": "How should we interpret the tradeoffs?",
                    "type": "evaluative",
                    "falsification_target": "counter-example",
                },
            ],
            "optimization_axes": ["speed", "accuracy"],
        }
    )

    assert id_map == {"SQ-a": "Q-1", "SQ-b": "Q-2"}
    assert [sub_question.id for sub_question in stage_1.sub_questions] == ["Q-1", "Q-2"]
    assert [sub_question.type for sub_question in stage_1.sub_questions] == ["empirical", "interpretive"]


def test_migrate_legacy_bundle_rewrites_legacy_sub_question_fields() -> None:
    """Legacy bundle evidence should carry Tyler `Q-*` ids after migration."""

    bundle = migrate_legacy_bundle(
        {
            "question": {
                "text": "What happened?",
                "time_sensitivity": "mixed",
                "scope_notes": "",
                "key_entities": [],
            },
            "sources": [
                {
                    "id": "S-1",
                    "url": "https://example.com",
                    "title": "Example",
                    "source_type": "academic",
                    "quality_tier": "authoritative",
                    "retrieved_at": "2026-04-08T00:00:00+00:00",
                }
            ],
            "evidence": [
                {
                    "id": "E-1",
                    "source_id": "S-1",
                    "content": "quoted finding",
                    "content_type": "quotation",
                    "sub_question_id": "SQ-a",
                }
            ],
            "gaps": [],
        },
        id_map={"SQ-a": "Q-1"},
    )

    payload = json.loads(bundle.model_dump_json())
    assert payload["evidence"][0]["sub_question_ids"] == ["Q-1"]
    assert payload["imported_from"].endswith("+legacy_tyler_fixture_migration")


def test_migrate_legacy_bundle_fails_loud_on_unknown_sub_question_id() -> None:
    """Unknown legacy ids should fail loudly instead of silently dropping evidence."""

    try:
        migrate_legacy_bundle(
            {
                "question": {
                    "text": "What happened?",
                    "time_sensitivity": "mixed",
                    "scope_notes": "",
                    "key_entities": [],
                },
                "sources": [
                    {
                        "id": "S-1",
                        "url": "https://example.com",
                        "title": "Example",
                        "source_type": "academic",
                        "quality_tier": "authoritative",
                        "retrieved_at": "2026-04-08T00:00:00+00:00",
                    }
                ],
                "evidence": [
                    {
                        "id": "E-1",
                        "source_id": "S-1",
                        "content": "quoted finding",
                        "content_type": "quotation",
                        "sub_question_id": "SQ-missing",
                    }
                ],
                "gaps": [],
            },
            id_map={"SQ-a": "Q-1"},
        )
    except ValueError as exc:
        assert "unknown sub-question id" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected unknown legacy sub-question id to fail loudly")
