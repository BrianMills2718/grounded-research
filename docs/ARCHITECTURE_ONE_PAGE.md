# Architecture One Page

Use this document for boundary and responsibility clarity.

- `docs/PLAN.md` owns sequencing and acceptance criteria
- `docs/CONTRACTS.md` owns inter-phase I/O and failure semantics
- `CLAUDE.md` owns operating rules and governance policy

## Thesis

The system should improve grounded research output by adding an adjudication layer above shared evidence, whether that evidence is imported or collected in-process.

The hypothesis is not "we need another research pipeline."

The hypothesis is:

- independent analyst passes over shared evidence create useful disagreement
- those disagreements can be canonicalized into a claim ledger
- some decision-critical disputes can be resolved with fresh evidence
- the resulting ledger is more useful than a plain narrative report

The product is the claim ledger. The report is a rendering of the ledger.

Current runtime note:

- the live runtime now also persists Tyler-native Stage 1-6 artifacts
- shipped `EvidenceBundle`, `AnalystRun`, `ClaimLedger`, and `FinalReport`
  remain compatibility or public-output surfaces
- that dual-surface state is intentional for now, but it is also a real source
  of documentation ambiguity and should be treated as explicit technical debt,
  not as an invisible default

## System Boundary

### This Project Owns

- cold-start question path: decomposition plus first-party web collection
- evidence-ingest adapters for upstream bundles
- independent analyst runs over shared evidence
- claim extraction
- semantic deduplication
- claim ledger construction
- dispute classification
- deterministic dispute routing
- narrow verification and arbitration
- final export for review and downstream handoff

### This Project Does Not Own In v1

- a retrieval-first product whose value is search novelty alone
- a new planner-first research pipeline
- a new production search orchestration layer

### Optional Upstream Inputs

- `research_v3` evidence packs
- manual evidence bundles
- other research engine outputs when useful

Approved external upstream candidates:

- STORM / `knowledge-storm`
- GPT Researcher

### Downstream Outputs

- human-review report
- trace artifact
- claim-ledger handoff for `onto-canon`

## Project Conventions

- operational policy values live in `config/config.yaml`
- prompts live in `prompts/` as YAML/Jinja2 templates
- prompts are rendered with `llm_client.render_prompt()`
- all LLM calls go through `llm_client`
- every real call passes `task=`, `trace_id=`, and `max_budget=`
- use `pyproject.toml` and a per-project `.venv`
- maintain a canonical Jupyter review notebook for end-to-end inspection
- treat external research engines as upstream inputs or baselines, not as the
  core adjudication runtime

## Runtime Layers

These are artifact and responsibility boundaries, not a mandatory process
topology. The product boundary is the typed artifacts and their validation.

### 1. Ingest

Input:

- upstream evidence bundle
- research question

Output:

- `ResearchQuestion`
- `EvidenceBundle`

Purpose:

- normalize imported evidence into project schemas
- preserve provenance, timestamps, and source quality
- mark question time-sensitivity

Boundary:

- code for adapter logic, normalization, IDs, dates, provenance
- LLMs only if semantic normalization is clearly needed

Adapter targets may include:

- `research_v3`
- STORM / `knowledge-storm`
- GPT Researcher

### 2. Analyze

Input:

- `ResearchQuestion`
- `EvidenceBundle`

Output:

- `list[AnalystRun]`

Purpose:

- run 3 independent analyses with different reasoning frames
- force explicit claims, assumptions, recommendations, and counterarguments

Preferred frame set after the core slice is stable:

- `verification_first`
- `structured_decomposition`
- `step_back_abstraction`

Non-negotiable:

- analysts never see each other's outputs

### 3. Canonicalize

Input:

- `list[AnalystRun]`

Output:

- `ClaimLedger`
- `list[Dispute]`

Purpose:

- extract raw claims
- semantically deduplicate into canonical claims
- preserve assumptions as first-class state rather than loose side notes
- preserve analyst provenance and evidence links
- classify disputes

Dispute types defined in the schema:

- `factual_conflict` — v1 core, routes to `verify`
- `interpretive_conflict` — v1 core, routes to `arbitrate`
- `preference_conflict` — v1 core, routes to `surface`; in TTY mode the system
  may ask the user for clarification before final export, otherwise the
  unresolved alternatives remain explicit in the report
- `ambiguity` — v1 core, routes to `surface`; material ambiguity may be surfaced
  to the user in TTY mode and otherwise remains explicit in the report/trace

Rule:

- LLMs may classify disputes semantically
- routing and status transitions remain code-owned

### 4. Adjudicate

Input:

- `ClaimLedger`
- `list[Dispute]`
- `EvidenceBundle`

Output:

- updated `ClaimLedger`
- `list[ArbitrationResult]`

Purpose:

- verify only decision-critical factual and interpretive disputes
- collect fresh evidence where useful
- update claim state based on new evidence

Rule:

- verification must reference newly retrieved evidence
- unresolved disputes remain explicit rather than being flattened away
- claim revisions are mechanically constrained: accepted updates require an
  allowed basis (`new_evidence`, `corrected_assumption`, or
  `resolved_contradiction`) plus cited support in structured state

### 5. Export

Input:

- `ResearchQuestion`
- `EvidenceBundle`
- `ClaimLedger`
- `list[Dispute]`

Output:

- Tyler `SynthesisReport`
- `report.md`
- `summary.md`
- `trace.json`
- Tyler-native handoff artifact for downstream use

Purpose:

- render recommendation, alternatives, disagreement map, evidence gaps, and
  flip conditions
- render assumptions and open questions when they exist in structured state
- validate grounding before export

Rule:

- synthesis renders structured state; it does not invent truth from scratch

## Current Core Entities

- `ResearchQuestion`
- `SourceRecord`
- `EvidenceItem`
- `EvidenceBundle`
- `AnalystRun`
- `RawClaim`
- `Claim`
- `Assumption`
- `Dispute`
- `VerificationQueryBatch`
- `ArbitrationResult`
- `ClaimLedger`
- Tyler `SynthesisReport`
- Tyler-native downstream handoff
- `PipelineWarning`
- `PipelineState`

## Planned-Future Entities

- `AssumptionLedger`

## Clean Hybrid Boundary

Use LLMs for:

- analyst reasoning
- claim extraction
- semantic deduplication
- dispute classification
- arbitration reasoning
- final rendering from structured state

Use deterministic code for:

- adapter normalization
- IDs
- schemas
- routing tables
- budgets
- thresholds
- trace serialization
- recency sorting
- grounding checks
- ledger state transitions

Use programmatic logic only when it is clearly better than an LLM on correctness, auditability, safety, or simplicity.

## Execution Modes

Use the simplest execution mode that satisfies the phase contract:

- structured calls for Phase -1 by default and for v1 analyst/dedup/classify/export work
- agent loops with tools for verification work that genuinely needs iterative search
- optional agent SDK comparison runs when evaluating whether agentic execution adds value

What does not change:

- all LLM calls still go through `llm_client`
- all calls still carry `task=`, `trace_id=`, `max_budget=`
- output contracts stay the same Pydantic models
- code-owned enforcement (IDs, routing, validation, trace) stays in code

## Recent-First Evidence Policy

Every source record should capture:

- `published_at`
- `retrieved_at`
- `source_type`
- `quality_tier`
- `recency_score`

Every question or plan context should capture:

- `time_sensitivity: stable | mixed | time_sensitive`

Policy:

- time-sensitive questions prefer recent authoritative sources first
- stable questions prefer authority first, then recency
- if recent evidence is weak, missing, or contradictory, that must appear in the report and trace

## Canonical Review Notebook

The canonical review surface currently lives under `docs/notebooks/` as a set
of phase and planning notebooks rather than one monolithic notebook.

Its purpose is to let the user review the project as an end-to-end journey:

- imported evidence
- analyst divergence
- claim ledger state
- dispute routing
- arbitration outcomes
- final export

Before full implementations exist, the notebook should still emit provisional artifacts for each phase.

## Scope and Deferrals

Canonical current/deferred status lives in:

- `docs/ROADMAP.md`
- `docs/FEATURE_STATUS.md`
- `docs/plans/CLAUDE.md`

See `docs/adr/0002-approved-external-reuse-strategy.md` for external reuse
decisions.
