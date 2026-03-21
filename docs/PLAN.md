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

The phases in this plan are artifact boundaries.

They are not a requirement to build one monolithic phase-runner or bespoke
workflow engine.

## Current Status

- repo initialized
- project instructions in place
- ADR recorded
- external reuse strategy recorded
- one-page architecture written
- v1 brief absorbed into this plan (deleted as redundant)
- domain model draft written (`docs/DOMAIN_MODEL.md`)
- scope matrix written
- Pydantic models defined (`src/grounded_research/models.py`)
- inter-phase contracts defined (`docs/CONTRACTS.md`)
- golden-set evidence fixture created (`tests/fixtures/session_storage_bundle.json`)
- canonical review notebook runs top-to-bottom with schema-shaped fixture artifacts
- documentation-governance layer present (`.claude/`, `docs/plans/`,
  `scripts/relationships.yaml`, validation scripts)
- a committed end-to-end implementation exists (`c57cd2c`), but it has not yet
  been reviewed and accepted against the canonical plan

## Governance Surfaces

The repo keeps a small governance layer for documentation and planning
discipline.

- `CLAUDE.md` is the canonical project operating guide
- `AGENTS.md` mirrors `CLAUDE.md`
- `docs/PLAN.md` is the canonical execution plan
- `docs/plans/` holds numbered per-task plans once concrete implementation work
  items begin
- `.claude/` hooks and `scripts/relationships.yaml` validate required reading
  and document coupling

This layer is in scope. It should reinforce the canonical docs, not replace
them or create a second planning authority.

## Draft Implementation Gate

The repo may contain implementation surfaces before they are accepted into the
project baseline.

Those implementations do not advance milestone status automatically.

Before any implementation slice is adopted, review it against:

- `CLAUDE.md`
- this plan
- `docs/CONTRACTS.md`
- `src/grounded_research/models.py`
- explicit verification expectations

Adopt an implementation slice only if it:

- matches the current milestone order
- respects the typed contracts
- does not smuggle in a broader architecture than the plan allows
- has a clear verification story

Otherwise, mark it as hold or discard and keep the docs as source of truth.

## Success Criteria

The smallest useful version passes if it can:

1. take a question plus an imported evidence bundle
2. run multiple independent analysts over that shared evidence
3. convert their outputs into a usable claim ledger
4. surface real decision-relevant disputes
5. resolve at least some factual or interpretive disputes with fresh evidence
6. write a grounded `report.md` and `trace.json`

## Execution Strategy Boundary

The repo owns:

- the typed artifacts
- the inter-phase contracts
- validation and grounding rules
- trace semantics

The repo does not require one executor implementation.

Execution modes available via `llm_client` (see `CLAUDE.md` for details):

- **Structured call**: default for phases where input fits in context
- **Agent loop with tools**: for phases requiring tool use (Phase 4)
- **Agent SDK** (claude-code, codex): available for experimentation

Phase -1 should compare structured calls against at least one agent SDK
path when practical. Output contracts stay the same regardless of mode.

## Execution Order

These phases are sequencing and acceptance boundaries, not a required concrete
runtime topology.

### Phase -1: Thesis Falsification

Goal:

- prove the disagreement signal is worth building around

Build:

- a small script that accepts a question plus an evidence bundle
- 3 independent analyst calls via `llm_client`
- 3 `AnalystRun`-shaped artifacts or equivalent analyst outputs
- a minimal claim extraction pass
- a compact manual-review artifact using the rubric below
- a reviewable trace artifact
- at least one baseline comparison path when practical:
  - manual or `research_v3` evidence
  - STORM or GPT Researcher output

Pass if:

- disagreements are not mostly framing noise
- at least some disputes are decision-relevant
- fresh evidence plausibly sharpens or changes at least some answers
- the imported external baseline is comparable enough to judge signal quality
- the chosen execution mode does not add more operational mess than analytical value

Fail if:

- the analysts mostly restate each other
- disagreements are mostly stylistic
- re-checking evidence rarely changes the outcome

Manual review rubric for Phase -1 output:

For each analyst pair (Alpha-Beta, Alpha-Gamma, Beta-Gamma), score:

1. **Substantive disagreement**: Do the analysts reach different conclusions
   or recommend different actions? (yes/no)
2. **Decision-relevant**: Would the disagreement change what a team actually
   does? (yes/no/marginal)
3. **Evidence-grounded**: Do the analysts cite different evidence for their
   positions, or just frame the same evidence differently? (different evidence /
   different framing / both)
4. **Resolvable**: Could targeted new evidence plausibly resolve the
   disagreement? (yes/no/unclear)

Pass threshold: at least 2 of 3 analyst pairs show substantive,
decision-relevant disagreement grounded in different evidence readings.

Promotion: `planned` → `live` (standalone script, no framework dependency)

Execution note:

- default to structured calls for the first live run
- compare against one agent SDK path when practical
- do not block the thesis test on workflow infrastructure

### Phase 0: Domain Model, Contracts, Trace, And Review Surface

Goal:

- finish design-method steps 3-5 before real orchestration

Build:

- `pyproject.toml`
- per-project `.venv`
- `config/config.yaml`
- `prompts/`
- `docs/DOMAIN_MODEL.md` (done)
- Pydantic schemas (done)
- `PipelineState` (done)
- trace serialization (done — `PipelineState.model_dump_json()`)
- dry-run CLI scaffold
- canonical notebook alignment (done)

Pass if:

- schemas validate (done)
- domain entities are defined at field level (done)
- inter-phase contracts and failure semantics are explicit (done)
- state serializes and deserializes cleanly (done)
- dry-run CLI writes a trace skeleton
- notebook still runs top-to-bottom with explicit artifacts (done)

Promotion: `partial` → `live` once an adopted `pyproject.toml`,
`config/config.yaml`, `prompts/`, and a dry-run CLI exist.

Execution note:

- `Phase 0` should keep the runtime boundary open
- do not overfit schemas and prompts to one executor style if the artifacts are executor-agnostic

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

Promotion: `fixture` → `live` once ingest adapter reads research_v3 `graph.yaml`
or manual JSON bundles.

### Phase 2a: Single Analyst (validation sub-slice)

Goal:

- prove a single analyst produces valid structured output before scaling to three

Build:

- one analyst call via `call_llm_structured`
- `prompts/analyst.yaml` template
- structured output parsing to `AnalystRun`

Pass if:

- structured output parses to valid `AnalystRun`
- claims reference real evidence IDs from the bundle
- at least 1 claim, 1 assumption, 1 recommendation produced

Promotion: `stub` → `live` once `prompts/analyst.yaml` and
`call_llm_structured` wiring exist.

Execution mode: structured call (v1). See agentic upgrade path below.

### Phase 2b: Three Independent Analysts

Goal:

- produce useful divergence over the same evidence set

Build:

- 3 parallel analyst runs with different frames or models
- structured claims, assumptions, recommendations, counterarguments
- abort logic when <2 analysts succeed

Pass if:

- analysts do not see each other's outputs (enforced by construction)
- fewer than 2 successful analysts aborts loudly
- at least some useful divergence appears on benchmark questions

Promotion: `stub` → `live` once 3 parallel calls are wired with distinct
frames/models.

Execution mode: structured calls in parallel (v1). See agentic upgrade path
below.

### Phase 2 Agentic Upgrade Path (post-v1)

v1 analysts use structured calls because the golden-set evidence bundle fits
in context. When evidence bundles grow beyond comfortable single-call context,
promote analysts to agentic execution with `python_tools`:

- `read_evidence(evidence_id)` — read a specific evidence item on demand
- `search_evidence(query)` — search within the evidence bundle
- `note_claim(statement, evidence_ids, confidence, reasoning)` — record a claim
- `note_assumption(statement, basis)` — record an assumption
- `submit_analysis(summary)` — finalize the structured output

The output contract (`AnalystRun`) does not change. The upgrade is in how the
LLM produces it, not in what it produces. This uses `llm_client`'s
`python_tools` agent loop.

### Phase 3a: Claim Extraction

Goal:

- gather all raw claims from analyst runs into a flat list

Build:

- extraction of `AnalystRun.claims` into `list[RawClaim]` with analyst provenance

Pass if:

- every `RawClaim` traces to an `AnalystRun`
- no claim text is invented beyond what the analyst stated

Note: try the simple approach first (gather `AnalystRun.claims` directly). Add
an LLM normalization pass only if claim phrasing varies too much to deduplicate.

Promotion: `stub` → `live` (likely simple Python, no LLM needed).

### Phase 3b: Semantic Deduplication

Goal:

- merge equivalent raw claims into canonical claims while preserving provenance

Build:

- LLM-based equivalence class grouping of `RawClaim` list
- merging into `Claim` objects with `source_raw_claim_ids` and `analyst_sources`

Pass if:

- each `Claim.source_raw_claim_ids` maps to real `RawClaim` IDs
- `Claim.analyst_sources` is populated
- similar claims are merged; distinct claims are kept separate
- malformed dedup output fails loudly with partial trace

Promotion: `stub` → `live` once dedup prompt + `call_llm_structured` are wired.

### Phase 3c: Ledger Assembly And Dispute Detection

Goal:

- build the canonical claim ledger and detect conflicts between claims

Build:

- LLM-based dispute classification (identifies conflicts, assigns `DisputeType`)
- deterministic routing via `DISPUTE_ROUTING` table
- `ClaimLedger` construction with ID assignment

Pass if:

- disputes reference real claim IDs
- `Dispute.route` matches `DISPUTE_ROUTING[dispute.dispute_type]`
- no phantom disputes (disputes between claims that don't actually conflict)
- a human can inspect the ledger and understand the conflicts

Promotion: `stub` → `live` once dispute classification prompt is wired.

### Phase 4: Verification And Arbitration (Agentic)

Goal:

- resolve decision-critical disputes by searching for fresh evidence and
  arbitrating based on what is found

Execution mode: agentic — one `acall_llm(..., python_tools=[...])` invocation
per decision-critical dispute. The agent iterates: search, read results, decide
if more evidence is needed, then arbitrate. This is the phase most naturally
suited to agentic execution because verification intrinsically requires tool
use.

Build:

- Python tool callables: `search_web`, `read_url`, `record_evidence`,
  `submit_arbitration`
- agent invocation per dispute via `llm_client` `python_tools` loop
- code-owned ledger update logic (applies `ArbitrationResult.claim_updates`)
- `max_turns` budget per dispute (configurable in `config/config.yaml`)

Pass if:

- arbitration references newly retrieved evidence (not paraphrase of existing)
- claim status updates are consistent with verdict
- `Dispute.resolved` set appropriately
- ledger updates remain internally consistent
- agent terminates via `submit_arbitration` tool, not by `max_turns` exhaustion
  (exhaustion produces `inconclusive` + warning)

Promotion: `stub` → `live` once search tools and agent invocation are wired.

Implementation path:

1. First, build Phase 4 as structured sub-slices (Phase 4a: query generation +
   Phase 4b: arbitration) to prove the contract works.
2. Then, merge into a single agentic invocation per dispute.
3. The output contract (`ArbitrationResult` + new `EvidenceItem` records) is
   the same in both implementations.

### Phase 4 Stepping Stone: Structured Sub-Slices

These are the initial implementation before the full agentic loop is wired.

**Phase 4a: Verification Query Generation**

- Input: verify-worthy `list[Dispute]`
- Output: `list[VerificationQueryBatch]`
- LLM calls: 1 structured call or 1 per dispute

**Phase 4b: Structured Arbitration**

- Input: `ClaimLedger` + `list[VerificationQueryBatch]` + fresh evidence
- Output: updated `ClaimLedger` + `list[ArbitrationResult]`
- LLM calls: 1 per dispute

### Phase 5: Grounded Export And Downstream Handoff

Goal:

- render the adjudicated state for both human review and downstream systems

Build:

- LLM-based report synthesis from ledger state
- grounding validation (code-owned, see `docs/CONTRACTS.md` Phase 5 rules)
- evidence-gap surfacing
- export of `report.md`, `trace.json`, and `DownstreamHandoff` artifact

Pass if:

- every material recommendation cites claim IDs
- every cited claim maps to evidence IDs and source records
- unresolved disputes remain visible
- evidence gaps remain explicit
- downstream handoff artifact preserves IDs and provenance

Promotion: `stub` → `live` once synthesis prompt + grounding validation + file
export are wired.

## Scope

See `docs/SCOPE_MATRIX_V2.md` for the canonical deferred/cut lists.

See `docs/adr/0002-approved-external-reuse-strategy.md` for the approved
external reuse strategy.

## Config Schema (Draft)

These keys will live in `config/config.yaml` once Phase 0 infrastructure
exists. This draft defines the contract so prompts and code can reference
them before the file is created.

```yaml
models:
  analyst: "gemini/gemini-2.5-flash"          # Phase 2 analyst calls
  claim_extraction: "gemini/gemini-2.5-flash"  # Phase 3a (if LLM needed)
  deduplication: "gemini/gemini-2.5-flash"     # Phase 3b equivalence grouping
  dispute_classification: "gemini/gemini-2.5-flash"  # Phase 3c
  arbitration: "gemini/gemini-2.5-flash"       # Phase 4 agent loop
  synthesis: "gemini/gemini-2.5-flash"         # Phase 5 report rendering

budgets:
  analyst_max_calls: 3                         # number of analyst runs
  analyst_min_successful: 2                    # abort threshold
  verification_max_turns: 10                   # max agent loop turns per dispute
  verification_max_disputes: 5                 # max disputes to verify
  pipeline_max_budget_usd: 5.0                 # total pipeline budget

analyst_frames:
  - "general"
  - "general"
  - "general"
  # post-v1: verification_first, structured_decomposition, step_back_abstraction

evidence_policy:
  default_time_sensitivity: "mixed"
  recency_weight: 0.5                          # weight for recency vs authority
```

## Prompt Inventory

Each prompt is a YAML/Jinja2 template in `prompts/`, loaded via
`llm_client.render_prompt()`.

| Prompt file | Phase | Input variables | Output schema |
|---|---|---|---|
| `analyst.yaml` | 2 | `question: ResearchQuestion`, `evidence: list[EvidenceItem]`, `frame: AnalystFrame` | `AnalystRun` (structured output) |
| `dedup.yaml` | 3b | `raw_claims: list[RawClaim]` | equivalence class grouping → `list[Claim]` |
| `dispute_classify.yaml` | 3c | `claims: list[Claim]` | dispute list with `DisputeType` per conflict |
| `arbitration.yaml` | 4 | `dispute: Dispute`, `claims: list[Claim]`, `evidence: list[EvidenceItem]`, `new_evidence: list[EvidenceItem]` | `ArbitrationResult` |
| `synthesis.yaml` | 5 | `question: ResearchQuestion`, `ledger: ClaimLedger`, `evidence_gaps: list[str]` | `FinalReport` (structured output) |

Phase 3a (claim extraction) likely does not need a prompt — it gathers
`AnalystRun.claims` directly. A normalization prompt may be added if
phrasing variation is too high for dedup.

Phase -1 (thesis falsification) uses `analyst.yaml` directly with 3 different
models. No additional prompts needed.

## Phase -1 Model Selection

For the thesis test, use three models from different families to maximize
genuine disagreement signal:

- `gemini/gemini-2.5-flash` (Google)
- `claude-sonnet-4-6` (Anthropic)
- `openrouter/openai/gpt-5-mini` (OpenAI)

Same-family models (e.g., 3 Gemini calls) would test prompt-variation
disagreement, not model-disagreement. The thesis claims multi-model
disagreement is useful, so the first test should use cross-family models.

## Immediate Next Step

Review and triage the committed implementation surfaces.

Specifically:

1. classify each major implementation surface as `accept`, `hold`, or `discard`
2. do not let a full-engine draft skip ahead of `Phase -1`
3. only after that adoption review, run or extend the smallest `Phase -1` slice
