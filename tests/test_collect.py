"""Tests for evidence collection helpers."""

from __future__ import annotations

import pytest

from grounded_research.collect import _anchor_queries, _extract_topic_anchors, generate_search_queries


def test_extract_topic_anchors_builds_phrase_and_acronym() -> None:
    """Capitalized topic phrases should produce stable search anchors."""
    anchors = _extract_topic_anchors(
        "What is the current evidence on Universal Basic Income and related labor outcomes?",
    )

    assert "Universal Basic Income" in anchors
    assert "UBI" in anchors


def test_anchor_queries_prepends_primary_anchor_when_missing() -> None:
    """Generated queries that omit the parent topic should be mechanically re-anchored."""
    anchored = _anchor_queries(
        [
            "heterogeneous labor-supply responses by age gender education",
            "UBI pilot employment effects Finland Alaska",
        ],
        ["Universal Basic Income", "UBI"],
    )

    assert anchored[0].startswith("Universal Basic Income ")
    assert anchored[1] == "UBI pilot employment effects Finland Alaska"


@pytest.mark.asyncio
async def test_generate_search_queries_subquestions_include_parent_topic_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sub-question query generation must keep the parent topic explicit."""
    # mock-ok: verifies local prompt wiring and anchoring around the external LLM boundary.
    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models):
        assert task == "query_generation"
        assert "Parent question:" in messages[1]["content"]
        assert "Required topic anchors:" in messages[1]["content"]
        assert "Universal Basic Income" in messages[1]["content"]
        return response_model(
            queries=[
                "heterogeneous labor-supply responses by age gender education",
                "UBI pilot employment effects Finland Alaska",
            ]
        ), {}

    monkeypatch.setattr("llm_client.acall_llm_structured", fake_acall_llm_structured)

    queries, query_to_sq = await generate_search_queries(
        question=(
            "What is the current evidence from academic literature, pilot programs, "
            "and governmental reports regarding the impact of Universal Basic Income "
            "on workforce participation rates?"
        ),
        trace_id="test-trace",
        max_budget=0.2,
        num_queries=3,
        sub_questions=[
            {
                "id": "SQ-1",
                "type": "comparative",
                "text": "How do UBI labor effects vary across demographic groups?",
                "falsification_target": "Evidence showing no subgroup variation.",
            }
        ],
    )

    assert queries[0].startswith("Universal Basic Income ")
    assert queries[1] == "UBI pilot employment effects Finland Alaska"
    assert query_to_sq[queries[0]] == "SQ-1"
    assert query_to_sq[queries[1]] == "SQ-1"
