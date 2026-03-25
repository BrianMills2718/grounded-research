# Grounded Research Adjudication

This file is the canonical operating guide for this project. `AGENTS.md` must
mirror it exactly. Edit this file first, then resync `AGENTS.md`.

## Purpose

Build an adjudication-centered grounded research system.

V1 is still judged primarily on adjudication quality, not retrieval novelty.
The current implementation supports two valid entry paths:

- raw question -> decomposition -> web collection -> adjudication
- imported evidence bundle -> adjudication

Its v1 job is:

- support cold-start question-to-report runs when the user starts from a raw question
- accept evidence from existing upstream systems or manual bundles when available
- run independent analyst passes over shared evidence
- canonicalize outputs into a claim ledger
- detect and classify disputes
- verify a narrow subset of disputes with fresh evidence
- export a report and trace that can be reviewed by humans and fed downstream

Primary optional upstream inputs:

- `research_v3`
- manual evidence bundles
- other research engines when useful

Primary downstream consumer:

- `onto-canon`

## Principles

### 1. Adjudication First

The novel product is the adjudication layer, not retrieval novelty by itself.

A first-party cold-start retrieval path is allowed and currently implemented.
Do not treat imported evidence as the only supported mode, and do not treat
retrieval as the main thesis unless the adjudication thesis is already proven.

V1 should focus on:

- multi-analyst disagreement over shared evidence
- claim extraction
- semantic deduplication
- dispute classification
- narrow evidence-backed arbitration

### 2. LLM-First Semantics

Default to LLM-based methods for semantic tasks.

This includes:

- analyst reasoning
- claim extraction
- semantic deduplication
- dispute classification
- arbitration reasoning
- final rendering from structured state

Use deterministic or string-based logic only when it is clearly superior in correctness, auditability, safety, or simplicity.

Do not build brittle heuristic cascades for work that is fundamentally semantic.

### 3. Clean Hybrid Boundaries

Hybrid approaches are encouraged only when the boundary is clean:

- LLMs for semantic judgment
- code for mechanical enforcement

Mechanical enforcement includes:

- ID assignment
- schema validation
- routing-table lookup
- budget enforcement
- counting and threshold checks
- trace serialization
- date parsing and recency sorting
- grounding checks against explicit IDs
- ledger state transitions

Avoid messy mixtures where both prompts and heuristics try to solve the same semantic problem.

### 4. Recent-First Evidence

Prioritize recent authoritative sources by default, especially for unstable or time-sensitive questions.

Publication date and recency must be captured explicitly in the evidence model, even when evidence is imported from upstream systems.

If recent evidence is weak, missing, or conflicts with older authoritative sources, surface that explicitly in the trace and final report.

Authority still beats freshness when the question is stable and recency is not materially relevant.

### 5. The Claim Ledger Is The Product

The canonical artifact is the claim ledger, not the prose report.

The report is a rendering of structured state:

- claims
- evidence chains
- disputes
- arbitration results
- uncertainties

Do not let synthesis invent structure that the ledger does not already contain.

### 6. Strong Typing And Loud Failure

- Use Pydantic models for stage contracts and pipeline state.
- Preserve partial trace state on failure.
- No silent degradation.
- No `except: pass`.
- Unknown or malformed stage outputs must fail loudly at the stage boundary.

### 7. Shared Runtime And Config Surfaces

Operational policy values belong in project config, typically `config/config.yaml`.

This includes:

- model assignments
- fallback maps
- analyst-frame selection
- adjudication limits
- verification budgets
- feature flags
- source-ranking and recency policy

All LLM calls must go through `llm_client`.

Required call kwargs on every real call:

- `task=`
- `trace_id=`
- `max_budget=`

Use `llm_client` for:

- completions
- structured output
- agent SDK routing
- shared observability
- prompt rendering

Do not hand-roll direct LiteLLM calls or subprocess wrappers.

This repo owns contracts, schemas, validation, and grounded artifacts.

It does not require one concrete executor architecture.

Treat pipeline phases as artifact boundaries, not as a mandate to build a
custom phase runner.

Execution modes available via `llm_client`:

- **Structured call** (`call_llm_structured`): default for phases where input
  fits in context and output is a single Pydantic model.
- **Agent loop with tools** (`acall_llm(..., python_tools=[...])`): for phases
  that intrinsically require tool use (searching, iterating). Expected for
  Phase 4 (verification/arbitration).
- **Agent SDK** (`claude-code`, `codex`): available for experimentation and
  comparison. Phase -1 should compare structured calls against at least one
  agent SDK path when practical.

Match the execution mode to the task. The output contracts (Pydantic models)
stay the same regardless of which execution mode produces them.

Do not build a bespoke workflow engine, agent loop, or tool-calling framework
in this repo. Use `llm_client`'s existing infrastructure.

### 8. Prompts As Data

All prompts belong in a `prompts/` directory as YAML/Jinja2 templates.

Load prompts with `llm_client.render_prompt()`.

Do not embed prompts as Python f-strings.

Do not add few-shot examples without explicit review.

### 9. Prove The Thesis With The Smallest Useful Slice

Do not build the full cathedral first.

The thesis to prove is:

1. independent multi-model analysis over shared evidence creates useful disagreement,
2. claims can be canonicalized into a ledger without collapsing into noise,
3. some decision-critical disputes can be re-evaluated with new evidence,
4. the final report can be grounded back to evidence through IDs.

Everything else is subordinate until this works.

### 10. Fixed Budgets Before Clever Stopping

Use explicit configurable budgets first:

- analyst call caps
- verification caps
- model fallback limits
- stage retry limits

Do not implement semantic novelty or diminishing-returns logic early unless traces show a real need.

### 11. Notebook-First Review Surface

This project should maintain a canonical Jupyter review notebook so the user can inspect the journey end-to-end.

The notebook is a review surface, not a scratchpad.

Before full implementations exist, each notebook phase must still emit explicit provisional artifacts and state:

- `input -> output`
- acceptance criteria
- `status`
- `execution_mode`

Keep notebook contracts aligned with docs, schemas, and tests.

### 12. Plan-Gated Implementation

Do not start code implementation in this repo until `docs/PLAN.md` exists and is current.

At minimum, the plan must define:

- current direction
- success criteria
- long-term execution phases
- deferred-but-retained capabilities
- immediate next step

If scope, sequencing, or acceptance criteria change, update `docs/PLAN.md` first.

If the change is architectural, update the relevant ADR before continuing.

### 13. Documentation Governance Is In Scope

This repo intentionally keeps a documentation-governance layer alongside the
core project docs.

Authority chain:

- `CLAUDE.md` is the canonical project operating guide
- `AGENTS.md` mirrors `CLAUDE.md`
- `docs/PLAN.md` is the canonical execution plan
- `docs/plans/` is the numbered per-task plan surface for concrete work items
- `.claude/` hooks and `scripts/relationships.yaml` enforce required reading and
  doc coupling

This governance layer is not a way around project policy and should not compete
with the canonical docs. Its job is to validate and reinforce those docs.

Local or newly committed implementation files do not become accepted project
state merely by existing in the worktree or history. Adoption requires explicit
review against the plan, contracts, and tests.

If the governance layer becomes stale or burdensome, fix it explicitly or
remove it explicitly. Do not silently ignore it while still treating it as
authoritative.

## Architecture Priorities

Keep the runtime architecture clean and layered:

1. Ingest
2. Analyze
3. Canonicalize
4. Adjudicate
5. Export

Do not turn internal substeps into a sprawling public stage taxonomy.

These layers are logical contracts, not a required process topology. The
product boundary is the typed artifacts and their validation, not one
mandatory orchestration style.

## Non-Negotiable v1 Rules

1. Models analyzing evidence must not see each other's outputs.
2. Every material recommendation must cite claim IDs.
3. Every cited claim must map to evidence IDs and source records.
4. Routing decisions must be deterministic in code, even when dispute classification is LLM-assisted.
5. A failed run with a rich partial trace is better than a polished but ungrounded report.
6. V1 may start from upstream evidence or from a raw question. The adjudication thesis remains primary even when the repo performs its own collection.

## Implementation Order

Build in this order:

1. domain model, contracts, typed schemas, and trace (done — `DOMAIN_MODEL.md`, `models.py`, `CONTRACTS.md`)
2. `pyproject.toml`, per-project `.venv`, `config/config.yaml`, `prompts/`, and a canonical review notebook
3. evidence-ingest adapters for upstream bundles plus the first-party question-to-evidence path
4. one grounded analyst over normalized evidence (Phase 2a)
5. three independent analysts (Phase 2b)
6. claim extraction (Phase 3a)
7. semantic deduplication (Phase 3b)
8. ledger assembly and dispute detection (Phase 3c)
9. verification query generation (Phase 4a)
10. arbitration and ledger update (Phase 4b)
11. grounded export and downstream handoff (Phase 5)
12. only then consider user steering, smarter stopping, and richer runtime checks

## Workflow

1. Update `docs/PLAN.md` before any architectural change.
2. Keep typed schemas and contracts at the center of implementation.
3. All LLM calls through `llm_client` with `task=`, `trace_id=`, `max_budget=`.
4. Commit at independently verified milestones.

## Commands

- `python -m pytest tests/`: run tests
- `pip install -e .`: install package into local `.venv`

## References

- `docs/PLAN.md` — execution plan and acceptance criteria
- `docs/CONTRACTS.md` — inter-phase data flow contracts
- `docs/ARCHITECTURE_ONE_PAGE.md` — system boundary and runtime layers
- `docs/SCOPE_MATRIX_V2.md` — canonical deferred/cut lists
- `docs/adr/` — architectural decision records
- `docs/notebooks/01_adjudication_review_journey.ipynb` — canonical review notebook
