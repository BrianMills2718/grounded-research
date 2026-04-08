"""Tests for deterministic URL-based source quality scoring.

Tyler V1 spec: URL lookup table, not LLM-based.
"""

from __future__ import annotations

import asyncio

import pytest

from grounded_research.source_quality import (
    _classify_domain,
    _extract_domain,
    score_source_quality,
)


class TestExtractDomain:
    def test_simple(self) -> None:
        assert _extract_domain("https://example.com/path") == "example.com"

    def test_www_stripped(self) -> None:
        assert _extract_domain("https://www.nytimes.com/article") == "nytimes.com"

    def test_subdomain_preserved(self) -> None:
        assert _extract_domain("https://ncbi.nlm.nih.gov/pubmed/123") == "ncbi.nlm.nih.gov"

    def test_empty_returns_empty(self) -> None:
        assert _extract_domain("") == ""


class TestClassifyDomain:
    # --- authoritative ---
    def test_gov_tld(self) -> None:
        assert _classify_domain("epa.gov") == "authoritative"

    def test_edu_tld(self) -> None:
        assert _classify_domain("stanford.edu") == "authoritative"

    def test_mil_tld(self) -> None:
        assert _classify_domain("defense.mil") == "authoritative"

    def test_who(self) -> None:
        assert _classify_domain("who.int") == "authoritative"

    def test_nature(self) -> None:
        assert _classify_domain("nature.com") == "authoritative"

    def test_nber(self) -> None:
        assert _classify_domain("nber.org") == "authoritative"

    def test_worldbank(self) -> None:
        assert _classify_domain("worldbank.org") == "authoritative"

    def test_ncbi_subdomain(self) -> None:
        assert _classify_domain("ncbi.nlm.nih.gov") == "authoritative"

    def test_pubmed(self) -> None:
        assert _classify_domain("pubmed.ncbi.nlm.nih.gov") == "authoritative"

    def test_ac_uk(self) -> None:
        assert _classify_domain("ox.ac.uk") == "authoritative"

    # --- reliable ---
    def test_reuters(self) -> None:
        assert _classify_domain("reuters.com") == "reliable"

    def test_arxiv(self) -> None:
        assert _classify_domain("arxiv.org") == "reliable"

    def test_bbc(self) -> None:
        assert _classify_domain("bbc.com") == "reliable"

    def test_github(self) -> None:
        assert _classify_domain("github.com") == "reliable"

    # --- unknown ---
    def test_wikipedia(self) -> None:
        assert _classify_domain("wikipedia.org") == "unknown"

    def test_medium(self) -> None:
        assert _classify_domain("medium.com") == "unknown"

    def test_reddit(self) -> None:
        assert _classify_domain("reddit.com") == "unknown"

    def test_random_domain(self) -> None:
        assert _classify_domain("some-random-blog.com") == "unknown"

    def test_empty(self) -> None:
        assert _classify_domain("") == "unknown"

    # --- unreliable ---
    def test_coursehero(self) -> None:
        assert _classify_domain("coursehero.com") == "unreliable"


class TestScoreSourceQuality:
    def test_scores_sources_in_place(self) -> None:
        """Integration test: score_source_quality updates bundle sources."""
        from grounded_research.models import EvidenceBundle, SourceRecord

        bundle = EvidenceBundle(
            question={"text": "test", "sub_questions": []},
            sources=[
                SourceRecord(id="S-001", url="https://epa.gov/report", title="EPA Report"),
                SourceRecord(id="S-002", url="https://medium.com/blog", title="Blog Post"),
                SourceRecord(id="S-003", url="https://reuters.com/article", title="Reuters"),
            ],
            evidence=[],
        )

        asyncio.run(score_source_quality(bundle, trace_id="test"))

        assert bundle.sources[0].quality_tier == "authoritative"
        assert bundle.sources[1].quality_tier == "unknown"
        assert bundle.sources[2].quality_tier == "reliable"
        assert bundle.sources[0].quality_score is not None
        assert bundle.sources[1].quality_score is not None
        assert bundle.sources[2].quality_score is not None

    def test_quality_score_applies_freshness_and_staleness_modifiers(self) -> None:
        """Final Stage 2 quality score should not collapse to tier mapping alone."""
        from datetime import datetime, timedelta, timezone

        from grounded_research.models import EvidenceBundle, SourceRecord

        bundle = EvidenceBundle(
            question={"text": "test", "sub_questions": []},
            sources=[
                SourceRecord(
                    id="S-001",
                    url="https://example.com/v1/docs",
                    title="Old Docs",
                    source_type="web_search",
                    published_at=datetime.now(timezone.utc) - timedelta(days=3650),
                ),
                SourceRecord(
                    id="S-002",
                    url="https://epa.gov/report",
                    title="EPA Report",
                    source_type="government_db",
                    published_at=datetime.now(timezone.utc) - timedelta(days=5),
                ),
            ],
            evidence=[],
        )

        asyncio.run(
            score_source_quality(
                bundle,
                trace_id="test",
                source_text_by_id={
                    "S-001": "This page has moved. Deprecated. Use v3 instead.",
                    "S-002": "Current official report issued this year.",
                },
            )
        )

        assert bundle.sources[0].quality_score is not None
        assert bundle.sources[1].quality_score is not None
        assert bundle.sources[0].quality_score < 0.5
        assert bundle.sources[1].quality_score > bundle.sources[0].quality_score

    def test_empty_bundle(self) -> None:
        """No crash on empty sources."""
        from grounded_research.models import EvidenceBundle

        bundle = EvidenceBundle(
            question={"text": "test", "sub_questions": []},
            sources=[],
            evidence=[],
        )
        asyncio.run(score_source_quality(bundle, trace_id="test"))
