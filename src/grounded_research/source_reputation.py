"""Persistent source reputation database for tracking web source quality.

Learns which domains produce good/bad content across grounded-research pipeline
runs. Stores per-encounter records and maintains aggregate domain-level stats.

DB location: ~/projects/data/source_reputation.db (alongside llm_observability.db).
Uses stdlib sqlite3 only — no external dependencies.

Design decisions:
- Domain is the primary aggregation key (not URL) because reputation is a
  property of the publisher, not individual pages.
- Encounter-level records preserve full provenance for debugging.
- Auto-blocking uses a configurable threshold (default: >10 encounters, <10%
  success rate) to prevent consistently broken domains from wasting fetch budget.
- All scores are optional — encounters can record just fetch success/failure
  without quality assessment.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Default DB path — alongside llm_observability.db
_DEFAULT_DB_PATH = Path.home() / "projects" / "data" / "source_reputation.db"

# Auto-block thresholds
_AUTO_BLOCK_MIN_ENCOUNTERS = 10
_AUTO_BLOCK_MAX_SUCCESS_RATE = 0.10

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS sources (
    domain TEXT PRIMARY KEY,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    fetch_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    fail_count INTEGER NOT NULL DEFAULT 0,
    avg_quality_score REAL,
    avg_novelty_score REAL,
    survival_rate REAL,
    blocked INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS source_encounters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    url TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    trace_id TEXT,
    fetch_success INTEGER NOT NULL,
    quality_score REAL,
    novelty_score REAL,
    claims_extracted INTEGER,
    claims_survived INTEGER,
    FOREIGN KEY (domain) REFERENCES sources(domain)
);

CREATE INDEX IF NOT EXISTS idx_encounters_domain ON source_encounters(domain);
CREATE INDEX IF NOT EXISTS idx_encounters_timestamp ON source_encounters(timestamp);
CREATE INDEX IF NOT EXISTS idx_encounters_trace_id ON source_encounters(trace_id);
"""


def extract_domain(url: str) -> str:
    """Extract the registrable domain from a URL.

    Strips www. prefix for consistency. Returns the netloc as-is if parsing
    fails (e.g., for non-standard URLs).
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain or url
    except Exception:
        return url


class SourceReputationDB:
    """SQLite-backed source reputation tracker.

    Thread-safe for single-writer usage (SQLite default). Connection is opened
    lazily and kept for the lifetime of the instance.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        """Lazy connection with WAL mode for read concurrency."""
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA_SQL)
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> SourceReputationDB:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def record_encounter(
        self,
        url: str,
        fetch_success: bool,
        *,
        trace_id: str | None = None,
        quality_score: float | None = None,
        novelty_score: float | None = None,
        claims_extracted: int | None = None,
        claims_survived: int | None = None,
    ) -> None:
        """Record a single source encounter and update domain aggregates.

        This is the primary write path — call it after each fetch attempt
        during evidence collection or verification.
        """
        domain = extract_domain(url)
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()

        # Insert encounter record
        conn.execute(
            """INSERT INTO source_encounters
               (domain, url, timestamp, trace_id, fetch_success,
                quality_score, novelty_score, claims_extracted, claims_survived)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                domain,
                url,
                now,
                trace_id,
                1 if fetch_success else 0,
                quality_score,
                novelty_score,
                claims_extracted,
                claims_survived,
            ),
        )

        # Upsert domain aggregate
        conn.execute(
            """INSERT INTO sources (domain, first_seen, last_seen, fetch_count,
                                    success_count, fail_count)
               VALUES (?, ?, ?, 1, ?, ?)
               ON CONFLICT(domain) DO UPDATE SET
                   last_seen = excluded.last_seen,
                   fetch_count = fetch_count + 1,
                   success_count = success_count + excluded.success_count,
                   fail_count = fail_count + excluded.fail_count""",
            (
                domain,
                now,
                now,
                1 if fetch_success else 0,
                0 if fetch_success else 1,
            ),
        )

        # Recompute averages from encounter history
        self._recompute_aggregates(domain)
        conn.commit()

    def _recompute_aggregates(self, domain: str) -> None:
        """Recompute avg scores and survival rate from encounter records."""
        conn = self._get_conn()
        row = conn.execute(
            """SELECT
                   AVG(quality_score) as avg_q,
                   AVG(novelty_score) as avg_n,
                   SUM(claims_survived) as total_survived,
                   SUM(claims_extracted) as total_extracted
               FROM source_encounters
               WHERE domain = ?""",
            (domain,),
        ).fetchone()

        if row is None:
            return

        survival_rate: float | None = None
        total_extracted = row["total_extracted"]
        total_survived = row["total_survived"]
        if total_extracted and total_extracted > 0:
            survival_rate = (total_survived or 0) / total_extracted

        conn.execute(
            """UPDATE sources SET
                   avg_quality_score = ?,
                   avg_novelty_score = ?,
                   survival_rate = ?
               WHERE domain = ?""",
            (row["avg_q"], row["avg_n"], survival_rate, domain),
        )

    def get_reputation(self, domain: str) -> dict[str, Any] | None:
        """Get aggregated reputation stats for a domain.

        Returns None if the domain has never been seen.
        """
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM sources WHERE domain = ?",
            (domain,),
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    def get_reputation_for_url(self, url: str) -> dict[str, Any] | None:
        """Convenience: extract domain from URL, then get reputation."""
        return self.get_reputation(extract_domain(url))

    def get_ranked_sources(
        self,
        limit: int = 20,
        min_encounters: int = 1,
    ) -> list[dict[str, Any]]:
        """Return sources ranked by composite quality (quality x survival).

        Sources with no quality data sort to the bottom. Blocked sources
        are excluded.
        """
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT *,
                   COALESCE(avg_quality_score, 0) * COALESCE(survival_rate, 0.5) AS composite_score
               FROM sources
               WHERE blocked = 0 AND fetch_count >= ?
               ORDER BY composite_score DESC, fetch_count DESC
               LIMIT ?""",
            (min_encounters, limit),
        ).fetchall()

        return [dict(r) for r in rows]

    def get_worst_sources(
        self,
        limit: int = 20,
        min_encounters: int = 3,
    ) -> list[dict[str, Any]]:
        """Return sources ranked by worst performance (lowest success rate).

        Useful for identifying domains to block.
        """
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT *,
                   CASE WHEN fetch_count > 0
                        THEN CAST(success_count AS REAL) / fetch_count
                        ELSE 0.0 END AS success_rate
               FROM sources
               WHERE fetch_count >= ?
               ORDER BY success_rate ASC, fetch_count DESC
               LIMIT ?""",
            (min_encounters, limit),
        ).fetchall()

        return [dict(r) for r in rows]

    def should_skip(self, domain: str) -> bool:
        """Check if a domain should be skipped (blocked or consistently terrible).

        Returns True if the domain is explicitly blocked or has >10 encounters
        with <10% success rate.
        """
        conn = self._get_conn()
        row = conn.execute(
            "SELECT blocked, fetch_count, success_count FROM sources WHERE domain = ?",
            (domain,),
        ).fetchone()

        if row is None:
            return False

        if row["blocked"]:
            return True

        if (
            row["fetch_count"] >= _AUTO_BLOCK_MIN_ENCOUNTERS
            and row["fetch_count"] > 0
            and (row["success_count"] / row["fetch_count"]) < _AUTO_BLOCK_MAX_SUCCESS_RATE
        ):
            return True

        return False

    def should_skip_url(self, url: str) -> bool:
        """Convenience: extract domain from URL, then check skip status."""
        return self.should_skip(extract_domain(url))

    def auto_block_check(self) -> list[str]:
        """Scan all domains and block those meeting auto-block criteria.

        Returns list of newly blocked domain names.
        """
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT domain, fetch_count, success_count
               FROM sources
               WHERE blocked = 0 AND fetch_count >= ?""",
            (_AUTO_BLOCK_MIN_ENCOUNTERS,),
        ).fetchall()

        newly_blocked: list[str] = []
        for row in rows:
            if row["fetch_count"] > 0:
                success_rate = row["success_count"] / row["fetch_count"]
                if success_rate < _AUTO_BLOCK_MAX_SUCCESS_RATE:
                    conn.execute(
                        "UPDATE sources SET blocked = 1, notes = COALESCE(notes, '') || ? WHERE domain = ?",
                        (
                            f"\nAuto-blocked: {row['success_count']}/{row['fetch_count']} "
                            f"success rate ({success_rate:.1%})",
                            row["domain"],
                        ),
                    )
                    newly_blocked.append(row["domain"])
                    logger.info(
                        "Auto-blocked domain %s: %d/%d success rate (%.1f%%)",
                        row["domain"],
                        row["success_count"],
                        row["fetch_count"],
                        success_rate * 100,
                    )

        if newly_blocked:
            conn.commit()

        return newly_blocked

    def block_domain(self, domain: str, reason: str = "manual") -> bool:
        """Manually block a domain. Returns True if the domain existed."""
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()

        # Ensure the domain record exists
        conn.execute(
            """INSERT INTO sources (domain, first_seen, last_seen)
               VALUES (?, ?, ?)
               ON CONFLICT(domain) DO NOTHING""",
            (domain, now, now),
        )

        conn.execute(
            "UPDATE sources SET blocked = 1, notes = COALESCE(notes, '') || ? WHERE domain = ?",
            (f"\nBlocked: {reason} ({now})", domain),
        )
        conn.commit()
        logger.info("Blocked domain %s: %s", domain, reason)
        return True

    def unblock_domain(self, domain: str) -> bool:
        """Unblock a domain. Returns True if the domain existed and was blocked."""
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()

        row = conn.execute(
            "SELECT blocked FROM sources WHERE domain = ?",
            (domain,),
        ).fetchone()

        if row is None:
            return False

        if not row["blocked"]:
            return False

        conn.execute(
            "UPDATE sources SET blocked = 0, notes = COALESCE(notes, '') || ? WHERE domain = ?",
            (f"\nUnblocked ({now})", domain),
        )
        conn.commit()
        logger.info("Unblocked domain %s", domain)
        return True

    def get_encounter_history(
        self,
        domain: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get recent encounter history for a domain."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM source_encounters
               WHERE domain = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (domain, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict[str, Any]:
        """Get overall database statistics."""
        conn = self._get_conn()

        total_domains = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        blocked_domains = conn.execute(
            "SELECT COUNT(*) FROM sources WHERE blocked = 1"
        ).fetchone()[0]
        total_encounters = conn.execute(
            "SELECT COUNT(*) FROM source_encounters"
        ).fetchone()[0]
        successful_encounters = conn.execute(
            "SELECT COUNT(*) FROM source_encounters WHERE fetch_success = 1"
        ).fetchone()[0]

        return {
            "total_domains": total_domains,
            "blocked_domains": blocked_domains,
            "active_domains": total_domains - blocked_domains,
            "total_encounters": total_encounters,
            "successful_encounters": successful_encounters,
            "overall_success_rate": (
                successful_encounters / total_encounters
                if total_encounters > 0
                else None
            ),
        }


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def _cli_stats(db: SourceReputationDB) -> None:
    """Print overall stats and top/bottom sources."""
    stats = db.get_stats()
    print("=== Source Reputation Database ===")
    print(f"Total domains:    {stats['total_domains']}")
    print(f"Active domains:   {stats['active_domains']}")
    print(f"Blocked domains:  {stats['blocked_domains']}")
    print(f"Total encounters: {stats['total_encounters']}")
    if stats["overall_success_rate"] is not None:
        print(f"Success rate:     {stats['overall_success_rate']:.1%}")
    print()

    top = db.get_ranked_sources(limit=10, min_encounters=2)
    if top:
        print("--- Top Sources (quality x survival) ---")
        for s in top:
            qs = f"q={s['avg_quality_score']:.2f}" if s["avg_quality_score"] is not None else "q=n/a"
            sr = f"sr={s['survival_rate']:.1%}" if s["survival_rate"] is not None else "sr=n/a"
            print(f"  {s['domain']:<40} {qs}  {sr}  fetches={s['fetch_count']}")
        print()

    worst = db.get_worst_sources(limit=10, min_encounters=3)
    if worst:
        print("--- Worst Sources (lowest success rate) ---")
        for s in worst:
            rate = s["success_count"] / s["fetch_count"] if s["fetch_count"] > 0 else 0
            blocked_tag = " [BLOCKED]" if s["blocked"] else ""
            print(
                f"  {s['domain']:<40} "
                f"success={s['success_count']}/{s['fetch_count']} ({rate:.0%})"
                f"{blocked_tag}"
            )


def _cli_block(db: SourceReputationDB, domain: str) -> None:
    """Block a domain."""
    db.block_domain(domain, reason="manual CLI block")
    print(f"Blocked: {domain}")


def _cli_unblock(db: SourceReputationDB, domain: str) -> None:
    """Unblock a domain."""
    if db.unblock_domain(domain):
        print(f"Unblocked: {domain}")
    else:
        print(f"Domain {domain} not found or not blocked.")


def _cli_lookup(db: SourceReputationDB, domain: str) -> None:
    """Look up a specific domain's reputation and history."""
    rep = db.get_reputation(domain)
    if rep is None:
        print(f"Domain {domain} not found in database.")
        return

    print(f"=== {domain} ===")
    print(f"First seen:     {rep['first_seen']}")
    print(f"Last seen:      {rep['last_seen']}")
    print(f"Fetches:        {rep['fetch_count']} ({rep['success_count']} ok, {rep['fail_count']} failed)")
    if rep["avg_quality_score"] is not None:
        print(f"Avg quality:    {rep['avg_quality_score']:.2f}")
    if rep["avg_novelty_score"] is not None:
        print(f"Avg novelty:    {rep['avg_novelty_score']:.2f}")
    if rep["survival_rate"] is not None:
        print(f"Survival rate:  {rep['survival_rate']:.1%}")
    print(f"Blocked:        {'yes' if rep['blocked'] else 'no'}")
    if rep["notes"]:
        print(f"Notes:          {rep['notes'].strip()}")

    history = db.get_encounter_history(domain, limit=10)
    if history:
        print(f"\n--- Recent encounters ({len(history)} shown) ---")
        for enc in history:
            ok = "ok" if enc["fetch_success"] else "FAIL"
            qs = f"q={enc['quality_score']:.2f}" if enc["quality_score"] is not None else ""
            print(f"  {enc['timestamp'][:19]}  {ok}  {qs}  {enc['url'][:60]}")


def _cli_autoblock(db: SourceReputationDB) -> None:
    """Run auto-block check and report results."""
    blocked = db.auto_block_check()
    if blocked:
        print(f"Auto-blocked {len(blocked)} domain(s):")
        for d in blocked:
            print(f"  {d}")
    else:
        print("No domains met auto-block criteria.")


def main() -> None:
    """CLI entry point for source reputation management."""
    import sys

    usage = (
        "Usage: python -m grounded_research.source_reputation <command> [args]\n"
        "\n"
        "Commands:\n"
        "  stats              Show overall stats and top/bottom sources\n"
        "  lookup DOMAIN      Show reputation and history for a domain\n"
        "  block DOMAIN       Manually block a domain\n"
        "  unblock DOMAIN     Unblock a domain\n"
        "  autoblock          Run auto-block check on all domains\n"
    )

    args = sys.argv[1:]
    if not args:
        print(usage)
        sys.exit(1)

    command = args[0]

    with SourceReputationDB() as db:
        if command == "stats":
            _cli_stats(db)
        elif command == "lookup" and len(args) >= 2:
            _cli_lookup(db, args[1])
        elif command == "block" and len(args) >= 2:
            _cli_block(db, args[1])
        elif command == "unblock" and len(args) >= 2:
            _cli_unblock(db, args[1])
        elif command == "autoblock":
            _cli_autoblock(db)
        else:
            print(f"Unknown command or missing arguments: {' '.join(args)}\n")
            print(usage)
            sys.exit(1)


if __name__ == "__main__":
    main()
