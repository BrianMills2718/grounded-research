# Plan

This is the canonical execution plan for `grounded-research`.

If the other docs explain why the project exists, this file explains what gets
built, in what order, and what counts as passing.

## Current Direction

The project is adjudication-first.

It is not starting as a new end-to-end research pipeline.

V1 consumes upstream evidence, runs independent analysts, builds a claim
ledger, detects disputes, verifies a narrow subset of them, and exports a
grounded report plus trace.

## Current Status

- repo initialized
- project instructions in place
- ADR recorded
- external reuse strategy recorded
- one-page architecture written
- v1 brief written
- scope matrix written
- canonical review notebook created
- no implementation code yet

## Success Criteria

The smallest useful version passes if it can:

1. take a question plus an imported evidence bundle
2. run multiple independent analysts over that shared evidence
3. convert their outputs into a usable claim ledger
4. surface real decision-relevant disputes
5. resolve at least some factual or interpretive disputes with fresh evidence
6. write a grounded `report.md` and `trace.json`

## Execution Order

### Phase -1: Thesis Falsification

Goal:

- prove the disagreement signal is worth building around

Build:

- a small script that accepts a question plus an evidence bundle
- 3 independent analyst calls via `llm_client`
- a minimal claim extraction pass
- a reviewable trace artifact
- at least one baseline comparison path when practical:
  - manual or `research_v3` evidence
  - STORM or GPT Researcher output

Pass if:

- disagreements are not mostly framing noise
- at least some disputes are decision-relevant
- fresh evidence plausibly sharpens or changes at least some answers
- the imported external baseline is comparable enough to judge signal quality

Fail if:

- the analysts mostly restate each other
- disagreements are mostly stylistic
- re-checking evidence rarely changes the outcome

### Phase 0: Contracts, Trace, And Review Surface

Goal:

- establish typed boundaries before real orchestration

Build:

- `pyproject.toml`
- per-project `.venv`
- `config/config.yaml`
- `prompts/`
- Pydantic schemas
- `PipelineState`
- trace serialization
- dry-run CLI scaffold
- canonical notebook alignment

Pass if:

- schemas validate
- state serializes and deserializes cleanly
- dry-run CLI writes a trace skeleton
- notebook still runs top-to-bottom with explicit artifacts

### Phase 1: Upstream Evidence Ingest

Goal:

- normalize imported evidence into internal schemas without losing provenance

Build:

- ingest adapters for upstream evidence bundles
- source normalization
- recency metadata handling
- evidence-bundle schema validation
- adapter contract for external upstream engines such as STORM or GPT Researcher

Pass if:

- imported evidence maps cleanly to `SourceRecord` and `EvidenceItem`
- provenance and timestamps survive
- structured gaps are visible when evidence is weak

### Phase 2: Independent Analysts

Goal:

- produce useful divergence over the same evidence set

Build:

- 3 independent analyst runs
- distinct reasoning frames
- structured claims, assumptions, recommendations, counterarguments

Pass if:

- analysts do not see each other's outputs
- fewer than 2 successful analysts aborts loudly
- at least some useful divergence appears on benchmark questions

### Phase 3: Claim Ledger

Goal:

- turn analyst prose into the canonical project artifact

Build:

- claim extraction
- semantic deduplication
- canonical claim ledger
- dispute detection
- deterministic routing

Pass if:

- claims preserve analyst and evidence provenance
- duplicate and phantom disputes stay manageable
- a human can inspect the ledger and understand the conflicts

### Phase 4: Narrow Verification

Goal:

- test whether targeted re-search can resolve some important disputes

Build:

- verification query generation
- targeted re-search
- arbitration for factual and interpretive conflicts
- claim status updates

Pass if:

- some disputes move to supported, revised, refuted, or inconclusive
- arbitration references newly retrieved evidence
- ledger updates remain internally consistent

### Phase 5: Grounded Export And Downstream Handoff

Goal:

- render the adjudicated state for both human review and downstream systems

Build:

- final report rendering
- grounding checks
- evidence-gap surfacing
- `report.md`
- `trace.json`
- downstream handoff artifact for `onto-canon`

Pass if:

- every material recommendation cites claim IDs
- every cited claim maps to evidence IDs and source records
- unresolved disputes remain visible
- evidence gaps remain explicit

## Deferred But Retained

These are part of the plan, but they follow stabilization of the core slice:

- explicit `ambiguity` dispute type with user clarification routing
- a canonical `AssumptionLedger`
- fixed named reasoning frames:
  - `verification_first`
  - `structured_decomposition`
  - `step_back_abstraction`
- persistent Stage `1v` caveats and warnings in pipeline state
- arbitration rule: claims change only with new evidence, corrected assumptions, or resolved contradictions
- explicit assumptions section in the final report
- validator preventing settled disputes from reappearing as unresolved

## Not In Scope For Now

- a new planner-first pipeline in this repo
- a new retrieval stack in this repo
- novelty or diminishing-returns stopping logic
- runtime evidence-laundering detection beyond structural checks
- Grok or X integration
- broad runtime anti-bias instrumentation

## Approved External Reuse

Approved for direct leverage as upstream providers, baselines, or adapter
targets:

- STORM / `knowledge-storm`
- GPT Researcher

Approved conditionally:

- LangGraph, but only if resumable stateful orchestration becomes necessary

Not approved as core runtime dependencies for v1:

- AutoGen
- DebateLLM
- MedAgents
- MetaGPT
- Free-MAD
- Exchange-of-Thought implementations

## Immediate Next Step

Build `Phase -1`.

Do not start with the full package skeleton unless the disagreement signal looks
real enough to justify the adjudication layer.
