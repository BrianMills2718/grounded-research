# Grounded Research Adjudication

<!-- GENERATED FILE: DO NOT EDIT DIRECTLY -->
<!-- generated_by: scripts/meta/render_agents_md.py -->
<!-- canonical_claude: CLAUDE.md -->
<!-- canonical_relationships: scripts/relationships.yaml -->
<!-- canonical_relationships_sha256: 2535f6f9faf6 -->
<!-- sync_check: python scripts/meta/check_agents_sync.py --check -->

This file is a generated Codex-oriented projection of repo governance.
Edit the canonical sources instead of editing this file directly.

Canonical governance sources:
- `CLAUDE.md` — human-readable project rules, workflow, and references
- `scripts/relationships.yaml` — machine-readable ADR, coupling, and required-reading graph

## Purpose

This file is the canonical operating guide for this project. `AGENTS.md` is a
generated projection maintained by the governance framework
(`--refresh-agents`). Edit this file first; regenerate AGENTS.md from it.

## Commands

- `python -m pytest tests/`: run tests
- `pip install -e .`: install package into local `.venv`

## Operating Rules

This projection keeps the highest-signal rules in always-on Codex context.
For full project structure, detailed terminology, and any rule omitted here,
read `CLAUDE.md` directly.

### Principles

### 1. Adjudication First

The novel product is the adjudication layer, not a new retrieval stack.

Do not rebuild planning, retrieval, and synthesis from scratch unless the adjudication thesis is already proven and a clear gap remains.

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

### Workflow

1. Update `docs/PLAN.md` before any architectural change.
2. Keep typed schemas and contracts at the center of implementation.
3. All LLM calls through `llm_client` with `task=`, `trace_id=`, `max_budget=`.
4. Commit at independently verified milestones.

## Machine-Readable Governance

`scripts/relationships.yaml` is the source of truth for machine-readable governance in this repo: ADR coupling, required-reading edges, and doc-code linkage. This generated file does not inline that graph; it records the canonical path and sync marker, then points operators and validators back to the source graph. Prefer deterministic validators over prompt-only memory when those scripts are available.

## References

- `docs/PLAN.md` — execution plan and acceptance criteria
- `docs/CONTRACTS.md` — inter-phase data flow contracts
- `docs/ARCHITECTURE_ONE_PAGE.md` — system boundary and runtime layers
- `docs/SCOPE_MATRIX_V2.md` — canonical deferred/cut lists
- `docs/adr/` — architectural decision records
- `docs/notebooks/01_adjudication_review_journey.ipynb` — canonical review notebook
