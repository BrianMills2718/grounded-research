# Plan

This is the canonical execution plan for `grounded-research`.

If the other docs explain why the project exists, this file explains what gets
built, in what order, and what counts as passing.

## Current Direction

The project is adjudication-centered.

The adjudication layer remains the thesis, but the current implementation
supports two entry modes:

- raw question -> decomposition + collection -> adjudication
- imported evidence bundle -> adjudication

V1 is not judged on retrieval novelty alone. It is judged on whether the
grounded output improves because of claim extraction, dispute handling, and
evidence-backed adjudication.

The phases in this plan are artifact boundaries.

They are not a requirement to build one monolithic phase-runner or bespoke
workflow engine.

## Current Status (2026-04-08)

**v0.1.0 shipped. 47/52 scorecard features implemented. Full pipeline operational, but the April 2026 clause-by-clause Tyler audit found additional live code/spec gaps.**

See `docs/ROADMAP.md` for the forward-looking plan and priorities.
See `docs/FEATURE_STATUS.md` for the complete scorecard mapping.
See `docs/COMPETITIVE_ANALYSIS.md` for SOTA comparison results.

### Current Execution Topology (2026-04-08)

When invoked with a question (`python engine.py "question"`):

```
Question → decompose_question_tyler_v1() → Tyler Stage 1 `DecompositionResult`
    ↓
Sub-questions → generate_search_queries_tyler_v1() → typed Stage 2 query plans by `query_role`
    ↓
shared web search (`tavily` / `exa` by plan) → fetch pages (parallel)
    ↓
score_source_quality() → deterministic authority/freshness/staleness `quality_score`
    ↓
Tyler Stage 2 `EvidencePackage` + sufficiency check per sub-question → gaps added
    ↓
compress_evidence() if > threshold → reduced bundle
    ↓
run_analysts_tyler_v1() → Tyler Stage 3 `AnalysisObject[]` + `stage3_attempts`
    ↓ (evidence leakage check on Tyler Stage 3 text)
canonicalize_tyler_v1() → Tyler Stage 4 `ClaimExtractionResult`
verify_disputes_tyler_v1() → Tyler Stage 5 `VerificationResult`
    ↓
collect_stage6a_user_guidance() when Tyler-routed disputes remain after Stage 5
    ↓
generate_tyler_synthesis_report() → Tyler SynthesisReport (canonical structured export)
    ↓
render_long_report() → markdown from Tyler Stage 6
    ↓
write_outputs() → report.md, summary.md, trace.json, handoff.json
```

Key definitions:
- **Decision-critical dispute**: `severity == "decision_critical"` in Dispute model. Factual conflicts where the answer depends on which side is correct.
- **Inconclusive arbitration**: Fresh evidence search found nothing new, or found ambiguous evidence. In `standard` mode this ends verification. In deeper modes it may trigger another round up to the configured cap.
- **Analytical mode** (`synthesis_mode: "analytical"`): Long report may infer beyond sources, marked with `[analytical inference]`. Claim ledger and trace remain grounded regardless.
- **Dedup fallback**: If LLM returns 0 groups, raw claims promoted 1:1 (no dedup, full provenance preserved).

Current operational notes:
- full pipeline implemented with configurable depth modes (`standard`, `deep`,
  `thorough`)
- raw-question collection uses shared-provider search via `open_web_retrieval`
  with Tavily as the quality-first default, not a bespoke workflow engine
- Stage 1 no longer runs a separate validation/retry layer in the live path;
  Tyler's prompt-level self-check is the local mitigation
- Stage 2 query diversification is now a lightweight model call that emits
  typed query plans and routes by query role instead of dual-provider fan-out
- Stage 2 final source scoring is now deterministic authority/freshness/
  staleness blending, not tier-only scoring
- `deep` and `thorough` now add goal-driven evidence extraction on persisted
  page text, while `standard` keeps the cheaper notes/key-section path
- deeper modes now allow multi-round arbitration when earlier rounds remain
  inconclusive
- `thorough` long-report rendering now uses sectioned synthesis when the word
  target crosses the configured threshold; `standard` keeps the single-call path
- runtime-safe benchmark policy now uses run-local observability DBs and
  explicit finite request timeouts for long runs
- tracked 6-question benchmark currently favors the pipeline over cached
  Perplexity deep research
- repo-local Tyler runtime migration, prompt-quality recovery, canonical
  cutover, and the first five local remediation phases are landed
- the remaining Tyler gaps are now explicit shared-infra or evaluation lanes,
  not known unresolved local Stage 1-6 contract/orchestration debt
- there is no active repo-local compatibility-deletion wave left in `main`;
  the current frontier is the evidence-backed gap ledger plus the remediation
  waves it implies
- canonical successful exports now center Tyler Stage 6 plus Tyler-native
  downstream handoff artifacts; legacy structured-report and handoff surfaces
  are no longer part of the live runtime path

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

## Active Plan Surfaces

Current open work is intentionally narrow:

- completed cross-repo evaluation wave:
  `docs/plans/tyler_literal_default_eval_wave1.md`
- completed review notebook:
  `docs/notebooks/29_tyler_literal_default_eval_wave1.ipynb`

- repo-local Tyler canonical cutover reference:
  `docs/plans/tyler_canonical_cutover.md`
- completed child waves under that cutover:
  `docs/plans/legacy_export_surface_deletion.md`,
  `docs/plans/stage45_projection_deletion.md`,
  `docs/plans/stage13_runtime_projection_cutover.md`,
  `docs/plans/isolated_compatibility_surface_deletion.md`,
  `docs/plans/current_shape_model_surface_deletion.md`,
  `docs/plans/stage5_internal_protocol_literalization.md`,
  `docs/plans/stage34_compatibility_protocol_deletion.md`
- there is currently no active repo-local implementation wave; the next
  concrete work is the faithful-Tyler remainder plan plus shared-infra
  follow-through in `llm_client` / `open_web_retrieval`
- the first frozen shared-eval comparison is complete:
  `output/tyler_literal_default_eval_wave1/summary.md` favored Tyler-literal
  over the archived calibrated legacy anchor on the tracked UBI case
- the second frozen shared-eval comparison is complete:
  `output/tyler_literal_default_eval_wave2_pfas/summary.md` again favored
  Tyler-literal over the archived calibrated legacy anchor on PFAS
- the third frozen shared-eval comparison is complete:
  `output/tyler_literal_default_eval_wave3_llm_swe/summary.md` again favored
  Tyler-literal over the archived calibrated legacy anchor on the technical
  `llm_swe` case
- the current frozen-eval gate is satisfied for the active implementation lane;
  broader eval is now optional unless a later regression wave needs it
- the remaining explicit uncertainty is shared-infra provider/model parity, not
  runtime-contract ambiguity in this repo
- active remainder plan:
  `docs/plans/tyler_faithful_execution_remainder.md`
- active audit wave:
  `docs/plans/tyler_spec_gap_audit_wave1.md`
- active audit-governance wave:
  `docs/plans/tyler_audit_governance_wave1.md`
- active remediation planner:
  `docs/plans/tyler_gap_remediation_wave1.md`
- planned remediation-support maintainability wave:
  `docs/plans/post_audit_maintainability_wave1.md`
- canonical gap ledger:
  `docs/TYLER_SPEC_GAP_LEDGER.md`
- canonical failure-analysis / prevention surface:
  `docs/TYLER_AUDIT_FAILURE_ANALYSIS.md`
- the active audit has already identified real local divergences in Stage 1,
  Stage 2, Stage 3, Stage 4, Stage 5, and Stage 6, so the previous
  "repo-local work complete" story is no longer accurate
- the new governance layer exists because earlier Tyler parity waves completed
  real migration and prompt work but still overclaimed clause-level closure
  before the ledger existed
- completed provider-cutover wave:
  `docs/plans/tavily_integration_wave1.md`
- there is currently no active repo-local implementation wave
- completed eval-expansion wave:
  `docs/plans/tyler_literal_default_eval_wave2.md`
- completed technical-breadth eval wave:
  `docs/plans/tyler_literal_default_eval_wave3_llm_swe.md`
- active shared-parity closure wave:
  `docs/plans/tyler_shared_parity_closure_wave1.md`
- supporting status notes:
  `docs/TYLER_FROZEN_EVAL_STATUS.md`,
  `docs/TYLER_SHARED_INFRA_OWNERSHIP.md`,
  `docs/TYLER_EXECUTION_STATUS.md`
- deferred depth continuation beyond Wave 1: `docs/plans/depth_modes.md`
- completed Wave 1 depth continuation reference:
  `docs/plans/depth_modes_wave1_execution.md`
- Tyler literal-parity completed repo-local recovery references:
  `docs/plans/tyler_literal_parity_refactor.md`,
  `docs/plans/tyler_literal_parity_benchmark_reanchor.md`,
  `docs/plans/tyler_literal_prompt_quality_recovery.md`,
  `docs/plans/tyler_stage3_model_role_recovery.md`,
  `docs/plans/tyler_stage6_decision_guidance_recovery.md`
- Tyler V1 reference map and follow-through:
  `docs/TYLER_V1_CURRENT_REPO_MAP.md`,
  `docs/plans/tyler_v1_followthrough.md`
- historical Tyler-spec reconciliation reference:
  `docs/plans/v1_spec_alignment.md`
- completed post-Wave-2 hardening reference:
  `docs/plans/post_wave2_cleanup_hardening.md`

Historical benchmark progression and comparative results live in:

- `docs/COMPETITIVE_ANALYSIS.md`
- `docs/JUDGE_CRITIQUES.md`
- benchmark output artifacts under `output/`

## Success Criteria

The smallest useful version passes if it can:

1. take a question plus an imported evidence bundle
2. run multiple independent analysts over that shared evidence
3. convert their outputs into a usable claim ledger
4. surface real decision-relevant disputes
5. resolve at least some factual or interpretive disputes with fresh evidence
6. write a grounded `report.md` and `trace.json`

Cross-phase gate (applies to all phases):

1. each phase promotion requires an end-to-end phase-boundary test (fixture,
   notebook, or CLI path), not just unit-level checks;
2. phase status may not be marked `live` when assertions are uncertain;
3. unresolved assumptions must be recorded before moving to the next phase.

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

Historical note:

- the detailed Phase 2a/2b/3a/3b/3c write-ups below predate the Tyler-native
  cutover and are retained mainly as design history
- the live runtime contract is the Tyler Stage 1-6 topology described above
- where those older sections mention `AnalystRun` or direct raw-claim
  extraction, read them as archived compatibility context rather than the
  canonical current path

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

Execution mode (current): structured 4a/4b sub-slices.
Phase 4 currently runs as:

- deterministic Tyler-literal query generation in `verify.py` for the selected
  disputes.
- Phase 4b (`arbitration.yaml`): one structured arbitration call per dispute with
  fresh evidence available.

Planned direction: converge these slices into one `llm_client`-managed agentic loop
after this baseline is stable.

Build:

- deterministic Tyler-literal verification query builder with explicit
  neutral/supporting/authoritative/dated query roles
- arbitration prompt/contract for evidence-driven verdicts with fresh evidence IDs
- code-owned ledger update logic (applies `ArbitrationResult.claim_updates`)
- `max_turns` is recorded and validated as a phase-gate control (configurable in
  `config/config.yaml`)
- dispute-failure policy and warning model for partial recovery and hard failures

Pass if:

- arbitration references newly retrieved evidence (not paraphrase of existing)
- all non-`inconclusive` verdicts include `new_evidence_ids` proving fresh
  evidence was consulted
- claim status updates are consistent with verdict
- `Dispute.resolved` set only when evidence-driven rationale is attached
- ledger updates remain internally consistent
- structured arbitration returns a typed `ArbitrationResult` for every routed
  dispute path; `inconclusive` outcomes must include a typed warning reason

Fail if:

- any non-`inconclusive` verdict has no fresh evidence IDs
- partial failures lose trace coverage (no `adjudicate` warnings persisted)
- contract-breaking or schema-breaking data is generated
- any `inconclusive` result is emitted without a warning-compatible rationale
- phase-local warnings are dropped from trace

Promotion: `stub` → `live` once structured 4a/4b execution and warning persistence are stable.

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
- LLM calls: 1 structured call for the entire batch
- Acceptance: each batch must bind query batches to a dispute and include
  freshness or recency expectations

**Phase 4b: Structured Arbitration**

- Input: `ClaimLedger` + `list[VerificationQueryBatch]` + fresh evidence
- Output: updated `ClaimLedger` + `list[ArbitrationResult]`
- LLM calls: 1 per dispute where fresh evidence is actually retrieved
- Acceptance: all non-`inconclusive` results include evidence updates;
  `inconclusive` responses must include warning reason and persisted trace entry

### Phase 5: Grounded Export And Downstream Handoff

Goal:

- render the adjudicated state for both human review and downstream systems

Build:

- Tyler-native synthesis from Stage 5 state
- grounding validation (code-owned, see `docs/CONTRACTS.md` Phase 5 rules)
- evidence-gap surfacing
- export of `report.md`, `summary.md`, `trace.json`, and Tyler-native handoff artifact

Pass if:

- every material recommendation cites Tyler claim excerpts
- every cited claim maps to source references and source records
- unresolved disputes remain visible
- evidence gaps remain explicit
- downstream handoff artifact preserves IDs and provenance

Promotion: `stub` → `live` once synthesis prompt + grounding validation + file
export are wired.

## Scope

See `docs/FEATURE_STATUS.md` for the current implementation status and `v1_Pruning_Scorecard.xlsx` for the original scorecard.

See `docs/adr/0002-approved-external-reuse-strategy.md` for the approved
external reuse strategy.
See `docs/adr/0004-agentic-verification-and-fail-loud-phase4.md` for phase 4
evidence and fail-loud requirements.

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
| `analyst.yaml` | legacy compatibility only | `question: ResearchQuestion`, `evidence: list[EvidenceItem]`, `frame: AnalystFrame` | `AnalystRun` (not part of the live runtime path) |
| `dedup.yaml` | 3b | `raw_claims: list[RawClaim]` | equivalence class grouping → `list[Claim]` |
| `dispute_classify.yaml` | 3c | `claims: list[Claim]` | dispute list with `DisputeType` per conflict |
| `arbitration.yaml` | 4 | `dispute: Dispute`, `claims: list[Claim]`, `evidence: list[EvidenceItem]`, `new_evidence: list[EvidenceItem]` | `ArbitrationResult` |
| `tyler_v1_synthesis.yaml` | 5 | Tyler Stage 1/2/4/5 structured state | `SynthesisReport` (canonical structured output) |

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

There is no open repo-local hardening wave at the moment.

Current stop line:

1. preserve the runtime-safe fixture benchmark path and saved benchmark anchors
2. do not reopen solved repo-local Tyler contract or prompt-recovery work
   without a new benchmark-triggered diagnosis
3. treat remaining provider/model/search-stack parity gaps as shared-infra work
4. use `prompt_eval` for future prompt/model/export comparisons before opening
   another local refactor wave

Current reference surfaces:

- `docs/plans/tyler_literal_parity_refactor.md`
- `docs/plans/tyler_literal_parity_benchmark_reanchor.md`
- `docs/plans/tyler_literal_prompt_quality_recovery.md`
- `docs/plans/thorough_benchmark_preservation_wave1.md`
