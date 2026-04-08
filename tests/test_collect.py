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
from grounded_research.models import EvidenceItem, Stage2QueryPlan
from grounded_research.tyler_v1_models import DecompositionResult, ResearchPlan, StageSummary, SubQuestion


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
    async def fake_acall_llm_structured(model, messages, response_model, task, trace_id, max_budget, fallback_models, **kwargs):
        assert task == "query_generation"
        assert "timeout" not in kwargs
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


def _tyler_stage1_result() -> DecompositionResult:
    return DecompositionResult(
        core_question="What is the current evidence?",
        sub_questions=[
            SubQuestion(
                id="Q-1",
                question="What did pilot A show?",
                type="empirical",
                research_priority="high",
                search_guidance="official reports and evaluations",
            ),
            SubQuestion(
                id="Q-2",
                question="How should mixed findings be interpreted?",
                type="interpretive",
                research_priority="medium",
                search_guidance="reviews and critiques",
            )
        ],
        optimization_axes=["employment vs broader welfare"],
        research_plan=ResearchPlan(
            what_to_verify=["employment effect"],
            critical_source_types=["official docs", "academic"],
            falsification_targets=["contradictory RCT result", "N/A"],
        ),
        stage_summary=StageSummary(
            stage_name="Stage 1: Intake & Decomposition",
            goal="goal",
            key_findings=["k1", "k2", "k3"],
            decisions_made=["d1"],
            outcome="outcome",
            reasoning="reasoning",
        ),
    )


@pytest.mark.asyncio
async def test_collect_evidence_routes_tyler_query_plans_by_provider_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tyler Stage 2 should route Tavily and Exa queries by typed query plan."""

    async def fake_generate_search_queries_tyler_v1(*args, **kwargs):
        return [
            Stage2QueryPlan(
                provider="tavily",
                query_role="keyword_rewrite",
                query_text="pilot A employment effect",
                sub_question_id="Q-1",
                search_depth="basic",
                result_detail="summary",
                corpus="general",
            ),
            Stage2QueryPlan(
                provider="exa",
                query_role="semantic_description",
                query_text="A detailed evaluation of pilot A with direct labor-market outcomes.",
                sub_question_id="Q-1",
                search_depth="advanced",
                result_detail="chunks",
                detail_budget=3,
                corpus="academic",
                retrieval_instruction="Prioritize sources aligned with this guidance: official reports and evaluations.",
            ),
        ], {"Q-1": 2}

    tavily_calls: list[dict[str, object]] = []
    exa_calls: list[dict[str, object]] = []

    async def fake_search_web(query: str, count: int = 10, freshness: str = "none", **kwargs):
        tavily_calls.append({"query": query, "freshness": freshness, **kwargs})
        return (
            '{"results": [{"title": "Pilot result", "url": "https://example.com/pilot", '
            '"description": "Search snippet", "age": "1 day", "score": 0.9, '
            '"published_at": "2026-01-01T00:00:00+00:00"}]}'
        )

    async def fake_search_web_exa(query: str, count: int = 5, **kwargs):
        exa_calls.append({"query": query, **kwargs})
        return (
            '{"results": [{"title": "Pilot semantic result", "url": "https://example.com/semantic", '
            '"description": "Semantic snippet", "age": "", "published_at": "2026-01-02T00:00:00+00:00"}]}'
        )

    async def fake_score_source_quality(bundle, trace_id, max_budget, source_text_by_id=None):
        for source in bundle.sources:
            source.quality_tier = "authoritative"
            source.quality_score = 0.91

    async def fake_fetch_page(url: str, question: str = "") -> str:
        return (
            '{"url": "https://example.com/pilot", "content_type": "text/html", '
            '"char_count": 321, "notes": "Page summary long enough to be included as evidence.", '
            '"key_section": "Key section long enough to be included as evidence and clearly relevant."}'
        )

    monkeypatch.setattr("grounded_research.collect.generate_search_queries_tyler_v1", fake_generate_search_queries_tyler_v1)
    monkeypatch.setattr("grounded_research.tools.web_search.search_web", fake_search_web)
    monkeypatch.setattr("grounded_research.tools.web_search.search_web_exa", fake_search_web_exa)
    monkeypatch.setattr("grounded_research.source_quality.score_source_quality", fake_score_source_quality)
    monkeypatch.setattr("grounded_research.collect.load_config", lambda: {"collection": {}})
    monkeypatch.setattr("grounded_research.collect.get_depth_config", lambda: {
        "evidence_extraction_enabled": False,
        "evidence_extraction_max_sources": 0,
        "evidence_extraction_items_per_source": 0,
        "evidence_extraction_max_chars": 0,
    })
    monkeypatch.setattr("grounded_research.collect.get_phase_concurrency_config", lambda: {})
    monkeypatch.setattr("grounded_research.tools.fetch_page.set_pages_dir", lambda path: None)
    monkeypatch.setattr("grounded_research.tools.fetch_page.fetch_page", fake_fetch_page)
    monkeypatch.setattr("grounded_research.collect.log_tool_call", lambda record: None)

    bundle, query_counts = await collect_evidence(
        question="What is the current evidence?",
        trace_id="trace-routed",
        max_sources=2,
        max_budget=0.1,
        tyler_stage_1_result=_tyler_stage1_result(),
        sub_questions=[sq.model_dump(mode="json") for sq in _tyler_stage1_result().sub_questions],
        return_query_counts=True,
    )

    assert query_counts == {"Q-1": 2}
    assert tavily_calls[0]["search_depth"] == "basic"
    assert tavily_calls[0]["result_detail"] == "summary"
    assert exa_calls[0]["search_depth"] == "advanced"
    assert exa_calls[0]["result_detail"] == "chunks"
    assert exa_calls[0]["detail_budget"] == 3
    assert exa_calls[0]["corpus"] == "academic"
    assert exa_calls[0]["retrieval_instruction"] == "Prioritize sources aligned with this guidance: official reports and evaluations."
    assert len(bundle.sources) == 2


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

    monkeypatch.setattr("grounded_research.tools.web_search.search_web", fake_search_web)
    async def _noop_exa(*a, **kw): return '{"results": []}'
    monkeypatch.setattr("grounded_research.tools.web_search.search_web_exa", _noop_exa)

    async def fake_score_source_quality(bundle, trace_id, max_budget, source_text_by_id=None):
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


@pytest.mark.asyncio
async def test_collect_evidence_preserves_all_matching_sub_question_tags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Evidence from a shared URL should keep every matching sub-question tag."""

    async def fake_generate_search_queries(*args, **kwargs):
        return [
            "ubi labor supply pilot",
            "ubi poverty pilot",
        ], {
            "ubi labor supply pilot": "SQ-1",
            "ubi poverty pilot": "SQ-2",
        }

    monkeypatch.setattr(
        "grounded_research.collect.generate_search_queries",
        fake_generate_search_queries,
    )

    async def fake_search_web(
        query: str,
        count: int = 10,
        freshness: str = "none",
        *,
        trace_id=None,
        task=None,
    ) -> str:
        assert trace_id == "trace-multitag"
        assert task == "collection.search"
        return (
            '{"results": [{"title": "Pilot result", "url": "https://example.com/pilot", '
            '"description": "Search snippet long enough to be included as evidence.", '
            '"age": "1 day"}]}'
        )

    monkeypatch.setattr("grounded_research.tools.web_search.search_web", fake_search_web)
    async def _noop_exa(*a, **kw): return '{"results": []}'
    monkeypatch.setattr("grounded_research.tools.web_search.search_web_exa", _noop_exa)

    async def fake_score_source_quality(bundle, trace_id, max_budget, source_text_by_id=None):
        for source in bundle.sources:
            source.quality_tier = "authoritative"

    monkeypatch.setattr("grounded_research.source_quality.score_source_quality", fake_score_source_quality)
    monkeypatch.setattr("grounded_research.collect.load_config", lambda: {"collection": {}})
    monkeypatch.setattr("grounded_research.tools.fetch_page.set_pages_dir", lambda path: None)
    monkeypatch.setattr(
        "grounded_research.collect.log_tool_call",
        lambda record: None,
    )

    async def fake_fetch_page(url: str, question: str = "") -> str:
        return (
            '{"url": "https://example.com/pilot", "content_type": "text/html", '
            '"char_count": 321, "notes": "Page summary long enough to be included as evidence.", '
            '"key_section": "Key section long enough to be included as evidence and clearly relevant."}'
        )

    monkeypatch.setattr("grounded_research.tools.fetch_page.fetch_page", fake_fetch_page)

    bundle = await collect_evidence(
        question="What happened in the UBI pilot?",
        trace_id="trace-multitag",
        max_sources=1,
        max_budget=0.1,
    )

    assert len(bundle.evidence) >= 3
    assert all(item.sub_question_ids == ["SQ-1", "SQ-2"] for item in bundle.evidence)


@pytest.mark.asyncio
async def test_collect_evidence_standard_mode_keeps_legacy_page_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Standard depth must not invoke the richer extraction path."""

    async def fake_generate_search_queries(*args, **kwargs):
        return ["ubi pilot"], {}

    async def fake_search_web(
        query: str,
        count: int = 10,
        freshness: str = "none",
        *,
        trace_id=None,
        task=None,
    ) -> str:
        return (
            '{"results": [{"title": "Pilot result", "url": "https://example.com/pilot", '
            '"description": "Search snippet long enough to be included as evidence.", '
            '"age": "1 day"}]}'
        )

    async def fake_score_source_quality(bundle, trace_id, max_budget, source_text_by_id=None):
        for source in bundle.sources:
            source.quality_tier = "authoritative"

    async def fake_fetch_page(url: str, question: str = "") -> str:
        return (
            '{"url": "https://example.com/pilot", "content_type": "text/html", '
            '"char_count": 321, "notes": "Page summary long enough to be included as evidence.", '
            '"key_section": "Key section long enough to be included as evidence and clearly relevant."}'
        )

    async def fake_extract_goal_driven_evidence(**kwargs):
        raise AssertionError("standard depth should not call goal-driven extraction")

    monkeypatch.setattr("grounded_research.collect.generate_search_queries", fake_generate_search_queries)
    monkeypatch.setattr("grounded_research.tools.web_search.search_web", fake_search_web)
    async def _noop_exa(*a, **kw): return '{"results": []}'
    monkeypatch.setattr("grounded_research.tools.web_search.search_web_exa", _noop_exa)
    monkeypatch.setattr("grounded_research.source_quality.score_source_quality", fake_score_source_quality)
    monkeypatch.setattr("grounded_research.collect.load_config", lambda: {"collection": {}})
    monkeypatch.setattr("grounded_research.collect.get_depth_config", lambda: {
        "evidence_extraction_enabled": False,
        "evidence_extraction_max_sources": 0,
        "evidence_extraction_items_per_source": 0,
        "evidence_extraction_max_chars": 0,
    })
    monkeypatch.setattr("grounded_research.collect.get_phase_concurrency_config", lambda: {})
    monkeypatch.setattr("grounded_research.tools.fetch_page.set_pages_dir", lambda path: None)
    monkeypatch.setattr("grounded_research.tools.fetch_page.fetch_page", fake_fetch_page)
    monkeypatch.setattr("grounded_research.collect.log_tool_call", lambda record: None)
    monkeypatch.setattr("grounded_research.collect._extract_goal_driven_evidence", fake_extract_goal_driven_evidence)

    bundle = await collect_evidence(
        question="What happened in the UBI pilot?",
        trace_id="trace-standard",
        max_sources=1,
        max_budget=0.1,
    )

    assert len(bundle.evidence) == 3
    assert any(item.content_type == "text" for item in bundle.evidence)
    assert any(item.content_type == "summary" for item in bundle.evidence)


@pytest.mark.asyncio
async def test_collect_evidence_deep_mode_uses_goal_driven_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deep depth should replace generic page notes with richer extracted items."""

    async def fake_generate_search_queries(*args, **kwargs):
        return ["ubi pilot"], {}

    async def fake_search_web(
        query: str,
        count: int = 10,
        freshness: str = "none",
        *,
        trace_id=None,
        task=None,
    ) -> str:
        return (
            '{"results": [{"title": "Pilot result", "url": "https://example.com/pilot", '
            '"description": "Search snippet long enough to be included as evidence.", '
            '"age": "1 day"}]}'
        )

    async def fake_score_source_quality(bundle, trace_id, max_budget, source_text_by_id=None):
        for source in bundle.sources:
            source.quality_tier = "authoritative"

    async def fake_fetch_page(url: str, question: str = "") -> str:
        return (
            '{"url": "https://example.com/pilot", "content_type": "text/html", '
            '"char_count": 3210, "file_path": "tmp-page.txt", '
            '"notes": "Page summary long enough to be included as evidence.", '
            '"key_section": "Key section long enough to be included as evidence and clearly relevant."}'
        )

    async def fake_extract_goal_driven_evidence(**kwargs):
        source = kwargs["source"]
        sq_ids = kwargs["sub_question_ids"]
        return [
            EvidenceItem(
                source_id=source.id,
                content="Finland pilot reported a short-run employment increase in one subgroup.",
                content_type="data_point",
                relevance_note="Direct pilot labor outcome evidence.",
                extraction_method="llm",
                sub_question_ids=sq_ids,
            ),
            EvidenceItem(
                source_id=source.id,
                content="The report also noted effects varied by demographic context.",
                content_type="text",
                relevance_note="Shows heterogeneity across participant groups.",
                extraction_method="llm",
                sub_question_ids=sq_ids,
            ),
        ]

    monkeypatch.setattr("grounded_research.collect.generate_search_queries", fake_generate_search_queries)
    monkeypatch.setattr("grounded_research.tools.web_search.search_web", fake_search_web)
    async def _noop_exa(*a, **kw): return '{"results": []}'
    monkeypatch.setattr("grounded_research.tools.web_search.search_web_exa", _noop_exa)
    monkeypatch.setattr("grounded_research.source_quality.score_source_quality", fake_score_source_quality)
    monkeypatch.setattr("grounded_research.collect.load_config", lambda: {"collection": {}})
    monkeypatch.setattr("grounded_research.collect.get_depth_config", lambda: {
        "evidence_extraction_enabled": True,
        "evidence_extraction_max_sources": 5,
        "evidence_extraction_items_per_source": 4,
        "evidence_extraction_max_chars": 4000,
    })
    monkeypatch.setattr("grounded_research.collect.get_phase_concurrency_config", lambda: {
        "evidence_extraction_max_concurrency": 2,
    })
    monkeypatch.setattr("grounded_research.tools.fetch_page.set_pages_dir", lambda path: None)
    monkeypatch.setattr("grounded_research.tools.fetch_page.fetch_page", fake_fetch_page)
    monkeypatch.setattr("grounded_research.collect.log_tool_call", lambda record: None)
    monkeypatch.setattr("grounded_research.collect._extract_goal_driven_evidence", fake_extract_goal_driven_evidence)

    bundle = await collect_evidence(
        question="What happened in the UBI pilot?",
        trace_id="trace-deep",
        max_sources=1,
        max_budget=0.1,
    )

    assert len(bundle.evidence) == 3
    assert [item.content_type for item in bundle.evidence[1:]] == ["data_point", "text"]


@pytest.mark.asyncio
async def test_collect_evidence_deep_mode_logs_gap_and_falls_back_on_extraction_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Depth extraction failures must stay explicit while preserving usable evidence."""

    async def fake_generate_search_queries(*args, **kwargs):
        return ["ubi pilot"], {}

    async def fake_search_web(
        query: str,
        count: int = 10,
        freshness: str = "none",
        *,
        trace_id=None,
        task=None,
    ) -> str:
        return (
            '{"results": [{"title": "Pilot result", "url": "https://example.com/pilot", '
            '"description": "Search snippet long enough to be included as evidence.", '
            '"age": "1 day"}]}'
        )

    async def fake_score_source_quality(bundle, trace_id, max_budget, source_text_by_id=None):
        for source in bundle.sources:
            source.quality_tier = "authoritative"

    async def fake_fetch_page(url: str, question: str = "") -> str:
        return (
            '{"url": "https://example.com/pilot", "content_type": "text/html", '
            '"char_count": 3210, "file_path": "tmp-page.txt", '
            '"notes": "Page summary long enough to be included as evidence.", '
            '"key_section": "Key section long enough to be included as evidence and clearly relevant."}'
        )

    async def fake_extract_goal_driven_evidence(**kwargs):
        raise RuntimeError("structured extraction broke")

    monkeypatch.setattr("grounded_research.collect.generate_search_queries", fake_generate_search_queries)
    monkeypatch.setattr("grounded_research.tools.web_search.search_web", fake_search_web)
    async def _noop_exa(*a, **kw): return '{"results": []}'
    monkeypatch.setattr("grounded_research.tools.web_search.search_web_exa", _noop_exa)
    monkeypatch.setattr("grounded_research.source_quality.score_source_quality", fake_score_source_quality)
    monkeypatch.setattr("grounded_research.collect.load_config", lambda: {"collection": {}})
    monkeypatch.setattr("grounded_research.collect.get_depth_config", lambda: {
        "evidence_extraction_enabled": True,
        "evidence_extraction_max_sources": 5,
        "evidence_extraction_items_per_source": 4,
        "evidence_extraction_max_chars": 4000,
    })
    monkeypatch.setattr("grounded_research.collect.get_phase_concurrency_config", lambda: {
        "evidence_extraction_max_concurrency": 1,
    })
    monkeypatch.setattr("grounded_research.tools.fetch_page.set_pages_dir", lambda path: None)
    monkeypatch.setattr("grounded_research.tools.fetch_page.fetch_page", fake_fetch_page)
    monkeypatch.setattr("grounded_research.collect.log_tool_call", lambda record: None)
    monkeypatch.setattr("grounded_research.collect._extract_goal_driven_evidence", fake_extract_goal_driven_evidence)

    bundle = await collect_evidence(
        question="What happened in the UBI pilot?",
        trace_id="trace-deep-error",
        max_sources=1,
        max_budget=0.1,
    )

    assert any("Depth evidence extraction failed" in gap for gap in bundle.gaps)
    assert len(bundle.evidence) == 3
