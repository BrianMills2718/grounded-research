# V1 Implementation Brief

## Objective

Build the smallest version of the project that can falsify the adjudication thesis cheaply.

Do not build a new full research pipeline first.

The v1 thesis is proven only if the system can:

1. consume a shared evidence bundle,
2. produce independent multi-model analyses over that same evidence,
3. canonicalize those analyses into a usable claim ledger,
4. identify real decision-relevant disagreements,
5. resolve at least some disagreements with fresh evidence,
6. generate a report and trace grounded back to claim and evidence IDs.

## Non-Negotiable Acceptance Criteria

- given a question plus imported evidence, the system writes `report.md` and `trace.json`
- every material recommendation cites claim IDs
- every cited claim maps to evidence IDs and source records
- at least some real disagreement is surfaced rather than flattened
- verification uses newly retrieved evidence, not only paraphrase
- failures preserve partial trace state
- the canonical review notebook runs top-to-bottom and shows provisional or real artifacts for each phase

## Execution Strategy

The v1 product is the adjudication contract, not one concrete executor.

The phases below are artifact boundaries.

They may be executed through:

- `structured` mode: `call_llm_structured` / `acall_llm_structured`
- `agent_sdk` mode: agent SDK models such as `claude-code` or `codex` through `llm_client`
- `workflow` mode: `llm_client.workflow_langgraph`, but only if explicit checkpoint/resume or approval pauses are actually needed

Default rule:

- prefer `structured` mode for deterministic schema-producing steps
- use `agent_sdk` selectively where search, tool use, or open-ended verification benefits from agentic behavior
- do not build a custom workflow engine first

## Phase -1: Thesis Falsification

This phase happens before substantial architecture work.

Build:

- a small script that takes a question plus an evidence bundle
- 3 analyst calls via `llm_client`
- a simple claim extraction pass
- a manual disagreement inspection workflow
- ideally one `structured` execution path first
- and, when practical, one `agent_sdk` comparison path on the same evidence bundle

Pass if:

- disagreements are not mostly framing noise
- at least some disputes appear decision-relevant
- fresh evidence plausibly changes or sharpens at least some answers
- the execution mode stays operationally simpler than the value it adds

If this fails, do not proceed with a larger adjudication build.

## What To Build First

### Phase 0: Domain Model, Contracts, Trace, And Review Surface

Build:

- `docs/DOMAIN_MODEL.md`
- `docs/CONTRACTS.md`
- `pyproject.toml`
- per-project `.venv`
- Pydantic schemas for pipeline entities
- config schema backed by `config/config.yaml`
- `prompts/` directory for YAML/Jinja2 prompt assets
- `PipelineState`
- trace serialization
- dry-run CLI scaffold
- canonical notebook at `docs/notebooks/01_adjudication_review_journey.ipynb`

Pass if:

- domain entities are defined at field level
- inter-phase contracts and failure semantics are explicit
- schema validation passes
- empty or fixture-backed state serializes cleanly
- CLI emits a valid trace skeleton
- notebook runs top-to-bottom and emits provisional artifacts
- repo conventions for config, prompts, notebook review, and `llm_client` call surfaces are in place

### Phase 1: Upstream Evidence Ingest

Build:

- adapters for imported evidence bundles
- source normalization
- recency-aware ranking metadata
- evidence-bundle schema validation

All prompts must be rendered with `llm_client.render_prompt()`.
All LLM calls must go through `llm_client` with `task=`, `trace_id=`, and `max_budget=`.

Pass if:

- imported evidence maps cleanly to internal `SourceRecord` and `EvidenceItem` schemas
- provenance and timestamps are preserved
- missing evidence is visible as structured gaps
- traces are readable enough to debug ingest failures

### Phase 2a: Single Analyst

Build:

- 1 structured analyst run
- evidence-linked claims, assumptions, recommendations, and counterarguments

Pass if:

- output parses to a valid `AnalystRun`
- evidence references resolve
- the result is reviewable in the notebook and trace

### Phase 2b: Independent Analysts

Build:

- 3 analyst runs in parallel
- distinct reasoning frames
- structured claims, assumptions, recommendations, counterarguments

Pass if:

- analysts remain structurally independent
- at least some benchmark prompts produce useful divergence
- fewer than 2 successful analysts aborts loudly

Note:

Once the core slice is stable, the default frame set should be:

- `verification_first`
- `structured_decomposition`
- `step_back_abstraction`

### Phase 3a: Claim Extraction

Build:

- claim extraction

Pass if:

- every extracted `RawClaim` retains analyst provenance
- evidence references remain intact

### Phase 3b: Semantic Deduplication

Build:

- semantic deduplication

Pass if:

- all merged claims retain raw-claim provenance
- phantom duplicates are reduced without collapsing distinct claims

### Phase 3c: Claim Ledger

Build:

- canonical claim ledger
- dispute detection
- deterministic routing table

Pass if:

- claims retain analyst and evidence provenance
- duplicate and phantom disputes stay manageable
- a human can inspect the ledger and understand what is in conflict

Note:

The claim ledger is the product. This is the heart of v1.

Later hardening should add:

- a first-class `AssumptionLedger`
- explicit `ambiguity` as a dispute type rather than relying only on broader mismatch buckets

### Phase 4a: Verification Query Generation

Build:

- verification query generation

Pass if:

- queries map cleanly to disputes
- queries are specific enough to plausibly retrieve new evidence

### Phase 4b: Narrow Verification

Build:

- targeted re-search
- arbitration for factual and interpretive conflicts only
- claim status updates

Pass if:

- some disputes are moved to supported, revised, refuted, or inconclusive
- arbitration references newly retrieved evidence
- ledger updates remain internally consistent

Rule to add once the core slice is stable:

- claims may change only because of new evidence, a corrected assumption, or a resolved contradiction

Do not include yet:

- preference steering
- ambiguity steering
- broad anti-bias runtime machinery

### Phase 5: Grounded Export And Downstream Handoff

Build:

- final report rendering
- grounding checks
- evidence-gap surfacing
- export of `report.md` and `trace.json`
- claim-ledger handoff artifact for downstream use, including `onto-canon`

Pass if:

- recommendation is claim-grounded
- unresolved disputes are visible, not hidden
- evidence gaps are explicit
- downstream handoff artifact preserves IDs and provenance

Later hardening should add:

- an explicit assumptions section distinct from `conditions_of_validity`
- a validator that prevents settled disputes from reappearing as unresolved report conflicts

## Default Technical Posture

- adjudication-first, not pipeline-first
- LLM-first for semantic tasks
- deterministic code for mechanical enforcement
- fixed budgets before clever stopping logic
- recent authoritative sources preferred for time-sensitive questions
- loud failure over silent degradation
- project policy values live in `config/config.yaml`
- prompts are YAML/Jinja2 assets in `prompts/`
- notebook review is a first-class surface, not an afterthought

## Explicit v1 Deferrals

- new retrieval orchestration
- new planning stack
- novelty or diminishing-returns stopping
- runtime evidence-laundering detection beyond structural checks
- Grok/X integration
- elaborate planner validation loops
- runtime self-bias instrumentation
- broad user-steering flows

## Planned After Core Stabilization

These are deferred for sequencing, not dropped from the plan:

- explicit `ambiguity` dispute type and routing to user clarification
- a canonical `AssumptionLedger` or equivalent first-class assumption state
- the stronger fixed reasoning-frame strategy
- persistent Stage `1v` caveats and warnings in pipeline state
- a hard arbitration rule limiting claim revisions to new evidence, corrected assumptions, or resolved contradictions
- an explicit assumptions section in the final report

## Developer Warnings

1. Do not rebuild `research_v3` inside this project.
2. Do not let synthesis invent structure absent from the ledger.
3. Do not overuse heuristics where semantic judgment is the real task.
4. Do not confuse interesting architecture with verified value.
5. A failed run with a rich trace is useful; a graceful-looking ungrounded run is not.
