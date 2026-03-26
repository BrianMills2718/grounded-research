"""Tests for evidence collection helpers."""

from __future__ import annotations

import pytest

from grounded_research.collect import (
    _anchor_queries,
    _extract_topic_anchors,
    collect_evidence,
    _score_search_result,
    _select_diverse,
    generate_search_queries,
)


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
    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, timeout):
        assert task == "query_generation"
        assert timeout == 120
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


def test_score_search_result_prefers_authoritative_pdf_sources() -> None:
    """Mechanical pre-fetch scoring should boost likely high-value study sources."""
    ranking_cfg = {
        "preferred_domain_patterns": ["nber.org", ".gov"],
        "deprioritized_domain_patterns": ["coursehero.com"],
        "preferred_title_terms": ["working paper", "evaluation"],
        "deprioritized_title_terms": ["study guide"],
        "pdf_bonus": 3,
        "preferred_domain_bonus": 5,
        "deprioritized_domain_penalty": 6,
        "preferred_title_bonus": 2,
        "deprioritized_title_penalty": 3,
        "quality_tier_bonus": {
            "authoritative": 8,
            "reliable": 3,
            "unknown": 0,
            "unreliable": -6,
        },
    }

    strong_score, _ = _score_search_result(
        {
            "url": "https://www.nber.org/system/files/working_papers/w25598/w25598.pdf",
            "title": "Universal Basic Income in the Developing World Working Paper",
            "description": "NBER working paper with detailed empirical evidence.",
        },
        ranking_cfg,
    )
    weak_score, _ = _score_search_result(
        {
            "url": "https://www.coursehero.com/file/251355593/Study-Guide.docx/",
            "title": "Evaluating Universal Basic Income Study Guide",
            "description": "Short secondary summary.",
        },
        ranking_cfg,
    )

    assert strong_score > weak_score


def test_select_diverse_ranks_within_query_before_round_robin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Within-query ranking should prefer strong sources while preserving diversity."""
    monkeypatch.setattr(
        "grounded_research.collect.get_collection_ranking_config",
        lambda: {
            "preferred_domain_patterns": ["nber.org", "worldbank.org"],
            "deprioritized_domain_patterns": ["coursehero.com"],
            "preferred_title_terms": ["working paper", "evidence"],
            "deprioritized_title_terms": ["study guide"],
            "pdf_bonus": 3,
            "preferred_domain_bonus": 5,
            "deprioritized_domain_penalty": 6,
            "preferred_title_bonus": 2,
            "deprioritized_title_penalty": 3,
            "quality_tier_bonus": {
                "authoritative": 8,
                "reliable": 3,
                "unknown": 0,
                "unreliable": -6,
            },
        },
    )

    selected = _select_diverse(
        [
            {
                "search_query": "q1",
                "url": "https://www.coursehero.com/file/1/",
                "title": "UBI Study Guide",
                "description": "summary",
            },
            {
                "search_query": "q1",
                "url": "https://www.nber.org/system/files/working_papers/w25598/w25598.pdf",
                "title": "Universal Basic Income Working Paper",
                "description": "Detailed empirical evidence from NBER working paper.",
            },
            {
                "search_query": "q2",
                "url": "https://openknowledge.worldbank.org/handle/10986/1234",
                "title": "Exploring Universal Basic Income: Evidence and Policy",
                "description": "World Bank evidence overview with program comparisons.",
            },
            {
                "search_query": "q2",
                "url": "https://example.com/blog-post",
                "title": "My UBI opinion",
                "description": "Blog commentary",
            },
        ],
        max_items=2,
    )

    assert [item["url"] for item in selected] == [
        "https://www.nber.org/system/files/working_papers/w25598/w25598.pdf",
        "https://openknowledge.worldbank.org/handle/10986/1234",
    ]


def test_select_diverse_prefers_prefetch_quality_tier_within_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prefetch quality should outrank a weaker same-query result."""
    monkeypatch.setattr(
        "grounded_research.collect.get_collection_ranking_config",
        lambda: {
            "preferred_domain_patterns": [],
            "deprioritized_domain_patterns": [],
            "preferred_title_terms": [],
            "deprioritized_title_terms": [],
            "pdf_bonus": 0,
            "preferred_domain_bonus": 0,
            "deprioritized_domain_penalty": 0,
            "preferred_title_bonus": 0,
            "deprioritized_title_penalty": 0,
            "quality_tier_bonus": {
                "authoritative": 8,
                "reliable": 3,
                "unknown": 0,
                "unreliable": -6,
            },
        },
    )

    selected = _select_diverse(
        [
            {
                "search_query": "q1",
                "url": "https://example.com/weaker",
                "title": "Weaker result",
                "description": "summary",
                "prefetch_quality_tier": "unknown",
            },
            {
                "search_query": "q1",
                "url": "https://example.com/stronger",
                "title": "Stronger result",
                "description": "summary",
                "prefetch_quality_tier": "authoritative",
            },
        ],
        max_items=1,
    )

    assert selected[0]["url"] == "https://example.com/stronger"


@pytest.mark.asyncio
async def test_collect_evidence_logs_fetch_and_jina_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Collection fetch orchestration should emit shared tool-call records."""

    logged_records = []

    async def fake_generate_search_queries(*args, **kwargs):
        return ["ubi pilot program"], {"ubi pilot program": "SQ-1"}

    monkeypatch.setattr(
        "grounded_research.collect.generate_search_queries",
        fake_generate_search_queries,
    )

    async def fake_search_web(query: str, count: int = 10, freshness: str = "none", *, trace_id=None, task=None):
        assert trace_id == "trace-collect"
        assert task == "collection.search"
        return (
            '{"results": [{"title": "Pilot result", "url": "https://example.com/pilot", '
            '"description": "Search snippet", "age": "1 day"}]}'
        )

    monkeypatch.setattr("grounded_research.tools.brave_search.search_web", fake_search_web)

    async def fake_score_source_quality(bundle, trace_id, max_budget):
        for source in bundle.sources:
            source.quality_tier = "authoritative"

    monkeypatch.setattr("grounded_research.source_quality.score_source_quality", fake_score_source_quality)
    monkeypatch.setattr("grounded_research.collect.load_config", lambda: {"collection": {}})
    monkeypatch.setattr("grounded_research.tools.fetch_page.set_pages_dir", lambda path: None)

    async def fake_fetch_page(url: str, question: str = "") -> str:
        return '{"url": "https://example.com/pilot", "error": "HTTP 403: Forbidden"}'

    async def fake_fetch_page_jina(url: str, question: str = "") -> str:
        return (
            '{"url": "https://example.com/pilot", "fetched_via": "jina_reader", '
            '"content_type": "text/markdown", "char_count": 321, "notes": "body", '
            '"key_section": "section"}'
        )

    monkeypatch.setattr("grounded_research.tools.fetch_page.fetch_page", fake_fetch_page)
    monkeypatch.setattr("grounded_research.tools.jina_reader.fetch_page_jina", fake_fetch_page_jina)
    monkeypatch.setattr("grounded_research.collect.log_tool_call", lambda record: logged_records.append(record))

    bundle = await collect_evidence(
        question="What happened in the UBI pilot?",
        trace_id="trace-collect",
        max_sources=1,
        max_budget=0.1,
    )

    assert len(bundle.sources) == 1
    assert bundle.sources[0].quality_tier == "authoritative"
    assert [record.provider for record in logged_records] == [
        "local_fetch_page",
        "local_fetch_page",
        "jina_reader",
        "jina_reader",
    ]
    assert [record.status for record in logged_records] == [
        "started",
        "failed",
        "started",
        "succeeded",
    ]
    assert all(record.trace_id == "trace-collect" for record in logged_records)
