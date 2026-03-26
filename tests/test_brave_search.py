"""Tests for shared-substrate Brave search wrapper."""

from __future__ import annotations

import asyncio
import json
import os
from types import SimpleNamespace

import pytest

from grounded_research.tools import brave_search


def test_search_web_returns_normalized_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the wrapper preserves downstream caller fields from retrieval hits."""
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
        def __init__(self, *, brave_api_key: str, tool_call_logger=None) -> None:
            assert brave_api_key == "test-key"
            captured["tool_call_logger"] = tool_call_logger

        def search(self, query, *, trace_id=None, task=None):  # type: ignore[no-untyped-def]
            assert query.top_k == 10
            assert query.providers == ("brave",)
            assert query.locale == "en"
            assert query.recency_days == 30
            captured["trace_id"] = trace_id
            captured["task"] = task
            return hits

    monkeypatch.setattr(brave_search, "OpenWebRetrievalClient", _Client)
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")

    payload = json.loads(
        asyncio.run(brave_search.search_web("who is brave", 10, "pm", trace_id="trace-1"))
    )
    assert payload["source"] == "Brave Search"
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
        },
    ]


def test_search_web_raises_when_api_key_missing() -> None:
    """Missing BRAVE_SEARCH_API_KEY should fail fast as before."""
    os.environ.pop("BRAVE_SEARCH_API_KEY", None)
    with pytest.raises(RuntimeError, match="BRAVE_SEARCH_API_KEY not set"):
        asyncio.run(brave_search.search_web("x"))


def test_search_web_returns_empty_results_when_no_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Search with zero results should normalize to a valid empty payload."""
    class _NoResultsError(brave_search.OpenWebRetrievalError):
        error_code = "OPEN_WEB_RETRIEVAL_ERROR"

    class _Client:
        def __init__(self, *, brave_api_key: str, tool_call_logger=None) -> None:
            assert brave_api_key == "test-key"

        def search(self, _query, *, trace_id=None, task=None) -> list:
            raise _NoResultsError("search returned no results", context={"query": "x"})

    monkeypatch.setattr(brave_search, "OpenWebRetrievalClient", _Client)
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")

    payload = json.loads(asyncio.run(brave_search.search_web("x")))
    assert payload["source"] == "Brave Search"
    assert payload["results"] == []
