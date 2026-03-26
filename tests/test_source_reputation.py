"""Tests for source reputation database.

Uses a temporary SQLite DB per test (no shared state, no mocks needed).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from grounded_research.source_reputation import (
    SourceReputationDB,
    extract_domain,
)


@pytest.fixture
def db(tmp_path: Path) -> SourceReputationDB:
    """Fresh reputation DB in a temp directory."""
    return SourceReputationDB(db_path=tmp_path / "test_reputation.db")


# ------------------------------------------------------------------
# extract_domain
# ------------------------------------------------------------------

class TestExtractDomain:
    def test_simple_url(self) -> None:
        assert extract_domain("https://example.com/path") == "example.com"

    def test_www_stripped(self) -> None:
        assert extract_domain("https://www.example.com/path") == "example.com"

    def test_subdomain_preserved(self) -> None:
        assert extract_domain("https://blog.example.com/post") == "blog.example.com"

    def test_port_included(self) -> None:
        assert extract_domain("http://localhost:8080/api") == "localhost:8080"

    def test_case_normalized(self) -> None:
        assert extract_domain("https://WWW.Example.COM/path") == "example.com"

    def test_bare_domain_fallback(self) -> None:
        # Non-URL strings fall back to the input
        assert extract_domain("not-a-url") == "not-a-url"


# ------------------------------------------------------------------
# record_encounter + get_reputation
# ------------------------------------------------------------------

class TestRecordEncounter:
    def test_first_encounter_creates_domain(self, db: SourceReputationDB) -> None:
        db.record_encounter("https://example.com/page1", fetch_success=True)
        rep = db.get_reputation("example.com")
        assert rep is not None
        assert rep["domain"] == "example.com"
        assert rep["fetch_count"] == 1
        assert rep["success_count"] == 1
        assert rep["fail_count"] == 0

    def test_multiple_encounters_aggregate(self, db: SourceReputationDB) -> None:
        db.record_encounter("https://example.com/page1", fetch_success=True)
        db.record_encounter("https://example.com/page2", fetch_success=True)
        db.record_encounter("https://example.com/page3", fetch_success=False)

        rep = db.get_reputation("example.com")
        assert rep is not None
        assert rep["fetch_count"] == 3
        assert rep["success_count"] == 2
        assert rep["fail_count"] == 1

    def test_quality_scores_averaged(self, db: SourceReputationDB) -> None:
        db.record_encounter(
            "https://example.com/p1", fetch_success=True,
            quality_score=0.8, novelty_score=0.6,
        )
        db.record_encounter(
            "https://example.com/p2", fetch_success=True,
            quality_score=0.4, novelty_score=0.2,
        )

        rep = db.get_reputation("example.com")
        assert rep is not None
        assert abs(rep["avg_quality_score"] - 0.6) < 0.01
        assert abs(rep["avg_novelty_score"] - 0.4) < 0.01

    def test_survival_rate_computed(self, db: SourceReputationDB) -> None:
        db.record_encounter(
            "https://example.com/p1", fetch_success=True,
            claims_extracted=10, claims_survived=8,
        )
        db.record_encounter(
            "https://example.com/p2", fetch_success=True,
            claims_extracted=10, claims_survived=2,
        )

        rep = db.get_reputation("example.com")
        assert rep is not None
        # total_survived=10, total_extracted=20 -> 0.5
        assert abs(rep["survival_rate"] - 0.5) < 0.01

    def test_trace_id_stored(self, db: SourceReputationDB) -> None:
        db.record_encounter(
            "https://example.com/page", fetch_success=True,
            trace_id="trace-abc-123",
        )
        history = db.get_encounter_history("example.com")
        assert len(history) == 1
        assert history[0]["trace_id"] == "trace-abc-123"

    def test_url_convenience_method(self, db: SourceReputationDB) -> None:
        db.record_encounter("https://example.com/page", fetch_success=True)
        rep = db.get_reputation_for_url("https://www.example.com/other")
        assert rep is not None
        assert rep["domain"] == "example.com"


# ------------------------------------------------------------------
# get_reputation (missing domain)
# ------------------------------------------------------------------

class TestGetReputation:
    def test_unknown_domain_returns_none(self, db: SourceReputationDB) -> None:
        assert db.get_reputation("never-seen.com") is None


# ------------------------------------------------------------------
# should_skip
# ------------------------------------------------------------------

class TestShouldSkip:
    def test_unknown_domain_not_skipped(self, db: SourceReputationDB) -> None:
        assert db.should_skip("unknown.com") is False

    def test_blocked_domain_skipped(self, db: SourceReputationDB) -> None:
        db.record_encounter("https://bad.com/page", fetch_success=True)
        db.block_domain("bad.com", reason="test")
        assert db.should_skip("bad.com") is True

    def test_low_success_rate_skipped(self, db: SourceReputationDB) -> None:
        # 11 encounters, 1 success = 9% < 10% threshold
        for i in range(11):
            db.record_encounter(
                f"https://terrible.com/page{i}",
                fetch_success=(i == 0),  # only first succeeds
            )
        assert db.should_skip("terrible.com") is True

    def test_decent_success_rate_not_skipped(self, db: SourceReputationDB) -> None:
        # 11 encounters, 3 successes = 27% > 10% threshold
        for i in range(11):
            db.record_encounter(
                f"https://ok.com/page{i}",
                fetch_success=(i < 3),
            )
        assert db.should_skip("ok.com") is False

    def test_few_encounters_not_skipped(self, db: SourceReputationDB) -> None:
        # Only 5 encounters (below threshold of 10), all failures
        for i in range(5):
            db.record_encounter(f"https://new.com/page{i}", fetch_success=False)
        assert db.should_skip("new.com") is False

    def test_should_skip_url_convenience(self, db: SourceReputationDB) -> None:
        db.record_encounter("https://bad.com/page", fetch_success=True)
        db.block_domain("bad.com")
        assert db.should_skip_url("https://www.bad.com/other") is True


# ------------------------------------------------------------------
# auto_block_check
# ------------------------------------------------------------------

class TestAutoBlockCheck:
    def test_auto_blocks_bad_domains(self, db: SourceReputationDB) -> None:
        # Create a terrible domain
        for i in range(12):
            db.record_encounter(
                f"https://spam.com/page{i}",
                fetch_success=False,
            )
        # And a good one
        for i in range(12):
            db.record_encounter(
                f"https://good.com/page{i}",
                fetch_success=True,
            )

        blocked = db.auto_block_check()
        assert "spam.com" in blocked
        assert "good.com" not in blocked

        # Verify it's now blocked in the DB
        rep = db.get_reputation("spam.com")
        assert rep is not None
        assert rep["blocked"] == 1

    def test_already_blocked_not_reblocked(self, db: SourceReputationDB) -> None:
        for i in range(12):
            db.record_encounter(f"https://spam.com/page{i}", fetch_success=False)
        db.block_domain("spam.com")

        # auto_block_check should not re-block
        blocked = db.auto_block_check()
        assert "spam.com" not in blocked


# ------------------------------------------------------------------
# block / unblock
# ------------------------------------------------------------------

class TestBlockUnblock:
    def test_block_new_domain(self, db: SourceReputationDB) -> None:
        db.block_domain("evil.com", reason="known spam")
        rep = db.get_reputation("evil.com")
        assert rep is not None
        assert rep["blocked"] == 1
        assert "known spam" in (rep["notes"] or "")

    def test_unblock_domain(self, db: SourceReputationDB) -> None:
        db.block_domain("evil.com")
        assert db.unblock_domain("evil.com") is True
        rep = db.get_reputation("evil.com")
        assert rep is not None
        assert rep["blocked"] == 0

    def test_unblock_nonexistent_returns_false(self, db: SourceReputationDB) -> None:
        assert db.unblock_domain("nonexistent.com") is False

    def test_unblock_not_blocked_returns_false(self, db: SourceReputationDB) -> None:
        db.record_encounter("https://ok.com/page", fetch_success=True)
        assert db.unblock_domain("ok.com") is False


# ------------------------------------------------------------------
# get_ranked_sources
# ------------------------------------------------------------------

class TestGetRankedSources:
    def test_ranking_order(self, db: SourceReputationDB) -> None:
        # High quality, good survival
        db.record_encounter(
            "https://great.com/p", fetch_success=True,
            quality_score=0.9, claims_extracted=10, claims_survived=9,
        )
        # Low quality, bad survival
        db.record_encounter(
            "https://mediocre.com/p", fetch_success=True,
            quality_score=0.3, claims_extracted=10, claims_survived=2,
        )

        ranked = db.get_ranked_sources(limit=10, min_encounters=1)
        assert len(ranked) == 2
        assert ranked[0]["domain"] == "great.com"
        assert ranked[1]["domain"] == "mediocre.com"

    def test_blocked_excluded(self, db: SourceReputationDB) -> None:
        db.record_encounter("https://blocked.com/p", fetch_success=True, quality_score=1.0)
        db.block_domain("blocked.com")
        db.record_encounter("https://ok.com/p", fetch_success=True, quality_score=0.5)

        ranked = db.get_ranked_sources(limit=10, min_encounters=1)
        domains = [r["domain"] for r in ranked]
        assert "blocked.com" not in domains
        assert "ok.com" in domains


# ------------------------------------------------------------------
# get_stats
# ------------------------------------------------------------------

class TestGetStats:
    def test_empty_db_stats(self, db: SourceReputationDB) -> None:
        stats = db.get_stats()
        assert stats["total_domains"] == 0
        assert stats["total_encounters"] == 0
        assert stats["overall_success_rate"] is None

    def test_populated_stats(self, db: SourceReputationDB) -> None:
        db.record_encounter("https://a.com/p", fetch_success=True)
        db.record_encounter("https://b.com/p", fetch_success=False)
        db.block_domain("b.com")

        stats = db.get_stats()
        assert stats["total_domains"] == 2
        assert stats["blocked_domains"] == 1
        assert stats["active_domains"] == 1
        assert stats["total_encounters"] == 2
        assert stats["successful_encounters"] == 1
        assert abs(stats["overall_success_rate"] - 0.5) < 0.01


# ------------------------------------------------------------------
# context manager
# ------------------------------------------------------------------

class TestContextManager:
    def test_context_manager_closes(self, tmp_path: Path) -> None:
        db_path = tmp_path / "ctx_test.db"
        with SourceReputationDB(db_path=db_path) as db:
            db.record_encounter("https://example.com/p", fetch_success=True)
        # Connection should be closed
        assert db._conn is None

        # Data should persist
        with SourceReputationDB(db_path=db_path) as db2:
            rep = db2.get_reputation("example.com")
            assert rep is not None
            assert rep["fetch_count"] == 1
