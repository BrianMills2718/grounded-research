# Architecture One Page

## Thesis

The system should improve grounded research output by adding an adjudication layer above existing evidence collection systems.

The hypothesis is not "we need another research pipeline."

The hypothesis is:

- independent analyst passes over shared evidence create useful disagreement
- those disagreements can be canonicalized into a claim ledger
- some decision-critical disputes can be resolved with fresh evidence
- the resulting ledger is more useful than a plain narrative report

The product is the claim ledger. The report is a rendering of the ledger.

## System Boundary

### This Project Owns

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

- a new end-to-end retrieval stack
- a new planner-first research pipeline
- a new production search orchestration layer

### Upstream Inputs

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

Planned dispute types after the core slice is stable:

- `factual_conflict`
- `interpretive_conflict`
- `preference_conflict`
- `ambiguity`

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
- claim revisions require new evidence, a corrected assumption, or a resolved contradiction
- unresolved disputes remain explicit rather than being flattened away

### 5. Export

Input:

- `ResearchQuestion`
- `EvidenceBundle`
- `ClaimLedger`
- `list[Dispute]`

Output:

- `FinalReport`
- `report.md`
- `trace.json`
- ledger handoff artifact for downstream use

Purpose:

- render recommendation, alternatives, disagreement map, assumptions, evidence gaps, and flip conditions
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
- `FinalReport`
- `DownstreamHandoff`
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

The canonical notebook should live at:

- `docs/notebooks/01_adjudication_review_journey.ipynb`

Its purpose is to let the user review the project as an end-to-end journey:

- imported evidence
- analyst divergence
- claim ledger state
- dispute routing
- arbitration outcomes
- final export

Before full implementations exist, the notebook should still emit provisional artifacts for each phase.

## Planned After Core Stabilization

These capabilities remain part of the project plan even if they do not land in
the smallest falsifiable slice:

- explicit `ambiguity` disputes with user-clarification routing
- a canonical `AssumptionLedger` or equivalent first-class assumption state
- fixed named reasoning frames rather than ad hoc analyst personas
- persistent Stage `1v` caveats and warnings in pipeline state
- arbitration rules that constrain claim changes to new evidence, corrected assumptions, or resolved contradictions
- an explicit assumptions section in the final report

## External Reuse Strategy

Directly leverage these as optional upstream providers or benchmark baselines:

- STORM / `knowledge-storm`
- GPT Researcher

Conditionally leverage:

- LangGraph, but only if resumable or interruptible workflow becomes a real
  implementation need

Do not use these as core runtime dependencies for v1:

- AutoGen
- DebateLLM
- MedAgents
- MetaGPT
- Free-MAD
- Exchange-of-Thought implementations

## v1 Scope

Keep v1 to the smallest falsifiable system:

1. typed schemas and full trace
2. upstream evidence-ingest adapters
3. one structured analyst
4. 3 independent analysts over imported evidence
5. claim extraction, deduplication, and dispute detection
6. narrow verification for factual and interpretive disputes
7. grounded report synthesis and downstream handoff
8. canonical review notebook

Defer:

- new retrieval orchestration
- new planning stack
- novelty stopping
- runtime bias instrumentation
- Grok/X integration
- elaborate planner retry loops
- advanced runtime anti-manipulation features
