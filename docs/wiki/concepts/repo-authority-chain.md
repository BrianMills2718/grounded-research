---
type: concept
status: active
updated: 2026-06-25
---

# Repo Authority Chain

The repository has historical plans, audits, roadmap docs, and delivery notes.
Maintainers need a deterministic reading order so stale documents do not create
accidental work.

## Order

1. Tyler gap ledger.
2. Tyler execution status.
3. Roadmap and concern register.
4. Current plan index.
5. Archived plans and handoffs.

## Why This Exists

Many Tyler remediation waves were executed and then superseded by later audits.
The plan archive preserves traceability, while the active index keeps current
work small enough for an implementer to reason about.

## Depends On

- `docs/plans/CLAUDE.md`
- `docs/PLAN.md`
- `docs/ROADMAP.md`
- `docs/CONCERNS.md`
