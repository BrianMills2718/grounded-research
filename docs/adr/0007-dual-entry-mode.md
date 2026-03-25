# ADR-0007: Dual Entry Mode (Supersedes ADR-0001)

## Status

Accepted (supersedes ADR-0001)

## Context

ADR-0001 ("Adjudication-First Scope") said v1 is not a full research pipeline
and will not rebuild retrieval. This was correct at the time but the
implementation evolved: the pipeline now supports cold-start question-to-report
runs with first-party evidence collection via Brave Search.

ADR-0001's constraint that "v1 consumes upstream evidence; it does not rebuild
a competing retrieval stack" no longer accurately describes the product.

## Decision

The repo supports two entry modes:

1. **Raw question → decomposition → web collection → adjudication → report**
2. **Imported evidence bundle → adjudication → report**

The adjudication thesis remains primary. The pipeline is judged on whether
claim extraction, dispute handling, and evidence-backed arbitration improve
the output — not on retrieval novelty.

First-party collection is a convenience feature, not the thesis. If the
collection step were removed, the adjudication pipeline should still be
the primary value.

## Consequences

- CLAUDE.md, README, ARCHITECTURE_ONE_PAGE, CONTRACTS, and PLAN updated
  to reflect dual-mode (commit f59d044)
- ADR-0001 is superseded but preserved for historical context
- Benchmarks compare the full pipeline (including collection) against
  Perplexity, because that's how users will run it
