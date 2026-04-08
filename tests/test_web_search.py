"""Tests for the shared-provider web search wrapper."""

from __future__ import annotations

import asyncio
import json
import os
from types import SimpleNamespace

import pytest

from grounded_research.tools import web_search


def test_search_web_returns_normalized_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """The wrapper should preserve the stable caller-facing result schema."""
    captured: dict[str, object] = {}
    hits = [
        SimpleNamespace(
            title="Example title",
            url="https://example.org",
            snippet="Example snippet",
            raw_payload={"age": "1 day"},
        ),
    ]

    class _Client:
        def __init__(self, *, tavily_api_key: str, tool_call_logger=None) -> None:
            assert tavily_api_key == "test-key"
            captured["tool_call_logger"] = tool_call_logger

        def search(self, query, *, trace_id=None, task=None):  # type: ignore[no-untyped-def]
            assert query.top_k == 10
            assert query.providers == ("tavily",)
            assert query.locale == "en"
            assert query.recency_days == 30
            captured["trace_id"] = trace_id
            captured["task"] = task
            return hits

        def close(self) -> None:
            return None

    monkeypatch.setattr(web_search, "OpenWebRetrievalClient", _Client)
    monkeypatch.setattr(web_search, "get_search_provider_config", lambda: {"provider": "tavily", "locale": "en"})
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    payload = json.loads(
        asyncio.run(web_search.search_web("who is tavily", 10, "pm", trace_id="trace-1"))
    )
    assert payload["source"] == "Tavily Search"
    assert payload["freshness"] == "pm"
    assert callable(captured["tool_call_logger"])
    assert captured["trace_id"] == "trace-1"
    assert captured["task"] == "collection.search"
    assert payload["results"] == [
        {
            "title": "Example title",
            "url": "https://example.org",
            "description": "Example snippet",
            "age": "1 day",
            "score": None,
            "published_at": None,
        },
    ]


def test_search_web_forwards_shared_retrieval_controls(monkeypatch: pytest.MonkeyPatch) -> None:
    """The wrapper should expose shared retrieval controls to local callers."""
    captured: dict[str, object] = {}

    class _Client:
        def __init__(self, *, tavily_api_key: str, tool_call_logger=None) -> None:
            assert tavily_api_key == "test-key"

        def search(self, query, *, trace_id=None, task=None):  # type: ignore[no-untyped-def]
            captured["query"] = query
            return []

        def close(self) -> None:
            return None

    monkeypatch.setattr(web_search, "OpenWebRetrievalClient", _Client)
    monkeypatch.setattr(web_search, "get_search_provider_config", lambda: {"provider": "tavily", "locale": "en"})
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    payload = json.loads(
        asyncio.run(
            web_search.search_web(
                "who is tavily",
                10,
                "pm",
                search_depth="basic",
                result_detail="summary",
                corpus="news",
                trace_id="trace-1",
            )
        )
    )

    query = captured["query"]
    assert query.search_depth == "basic"
    assert query.result_detail == "summary"
    assert query.corpus == "news"
    assert payload["results"] == []


def test_search_web_raises_when_provider_secret_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing provider credentials should fail loud for the configured provider."""
    monkeypatch.setattr(web_search, "get_search_provider_config", lambda: {"provider": "tavily", "locale": "en"})
    os.environ.pop("TAVILY_API_KEY", None)
    with pytest.raises(RuntimeError, match="TAVILY_API_KEY not set"):
        asyncio.run(web_search.search_web("x"))


def test_search_web_returns_empty_results_when_no_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Search with zero results should normalize to a valid empty payload."""

    class _NoResultsError(web_search.OpenWebRetrievalError):
        error_code = "OPEN_WEB_RETRIEVAL_ERROR"

    class _Client:
        def __init__(self, *, tavily_api_key: str, tool_call_logger=None) -> None:
            assert tavily_api_key == "test-key"

        def search(self, _query, *, trace_id=None, task=None) -> list:
            raise _NoResultsError("search returned no results", context={"query": "x"})

        def close(self) -> None:
            return None

    monkeypatch.setattr(web_search, "OpenWebRetrievalClient", _Client)
    monkeypatch.setattr(web_search, "get_search_provider_config", lambda: {"provider": "tavily", "locale": "en"})
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    payload = json.loads(asyncio.run(web_search.search_web("x")))
    assert payload["source"] == "Tavily Search"
    assert payload["results"] == []


def test_search_web_supports_exa_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """The shared wrapper should also normalize Exa through the same caller contract."""
    hits = [
        SimpleNamespace(
            title="Exa title",
            url="https://example.edu/exa",
            snippet="Exa snippet",
            raw_payload={},
        ),
    ]

    class _Client:
        def __init__(self, *, exa_api_key: str, tool_call_logger=None) -> None:
            assert exa_api_key == "exa-test-key"

        def search(self, query, *, trace_id=None, task=None):  # type: ignore[no-untyped-def]
            assert query.providers == ("exa",)
            return hits

        def close(self) -> None:
            return None

    monkeypatch.setattr(web_search, "OpenWebRetrievalClient", _Client)
    monkeypatch.setattr(web_search, "get_search_provider_config", lambda: {"provider": "exa", "locale": "en"})
    monkeypatch.setenv("EXA_API_KEY", "exa-test-key")

    payload = json.loads(asyncio.run(web_search.search_web("x")))
    assert payload["source"] == "Exa Search"
    assert payload["results"][0]["description"] == "Exa snippet"
