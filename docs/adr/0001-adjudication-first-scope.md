# ADR 0001: Adjudication-First Scope

## Status

Accepted

## Date

2026-03-21

## Context

The original project direction framed `grounded-research` as a new end-to-end
research pipeline with planning, retrieval, analysis, adjudication, and
synthesis.

That scope overlaps heavily with existing systems in the workspace:

- `research_v3` already owns evidence collection, provenance, and grounded
  report generation
- `onto-canon` already owns canonicalization-oriented downstream reasoning

The genuinely novel hypothesis is narrower:

- independent analyst runs over shared evidence produce useful disagreement
- those disagreements can be canonicalized into a claim ledger
- some decision-critical disputes can be clarified with fresh evidence

The user also wants a clean architecture, LLM-first semantics for semantic
tasks, and a Jupyter review surface that makes the project inspectable before
full implementation exists.

## Decision

`grounded-research` will start as an adjudication-first layer, not as a new
full research pipeline.

V1 will focus on:

- ingesting upstream evidence bundles
- running independent analyst passes
- extracting and deduplicating claims
- building a canonical claim ledger
- detecting and routing disputes
- verifying a narrow subset of disputes with fresh evidence
- exporting a grounded report, trace, and downstream handoff artifact

V1 will not rebuild:

- a competing planner-first pipeline
- a competing retrieval stack
- a new general-purpose synthesis system detached from the claim ledger

## Consequences

### Positive

- avoids duplicating `research_v3`
- tests the real thesis cheaply
- keeps the system composable with existing upstream and downstream projects
- makes the claim ledger the primary artifact from the start
- keeps the notebook review story simple and inspectable

### Negative

- the project depends on upstream evidence quality in v1
- some user-facing end-to-end demos will rely on imported bundles rather than
  a fully self-contained pipeline
- later expansion to a fuller pipeline will require a separate decision rather
  than happening by drift

## Follow-On Rules

1. Use LLMs by default for semantic transforms, and deterministic code for
   mechanical enforcement.
2. Treat recent-source preference as a first-class evidence policy.
3. Maintain a canonical Jupyter review notebook that mirrors the planned phase
   contracts.
4. If future work proposes rebuilding planning or retrieval in this repo,
   record a new ADR first.
