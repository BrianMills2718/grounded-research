# Grounded Research Adjudication

This file is the canonical operating guide for this project. `AGENTS.md` must mirror it exactly.

## Purpose

Build an adjudication-first layer for grounded research.

This project does not start as a new end-to-end research pipeline.

Its v1 job is narrower and more valuable:

- consume evidence from existing upstream systems or manual bundles
- run independent analyst passes over shared evidence
- canonicalize outputs into a claim ledger
- detect and classify disputes
- verify a narrow subset of disputes with fresh evidence
- export a report and trace that can be reviewed by humans and fed downstream

Primary upstream sources:

- `research_v3`
- manual evidence bundles
- other research engines when useful

Primary downstream consumer:

- `onto-canon`

## Core Operating Principles

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
- shared observability
- prompt rendering

Do not hand-roll direct LiteLLM calls or subprocess wrappers.

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

## Architecture Priorities

Keep the runtime architecture clean and layered:

1. Ingest
2. Analyze
3. Canonicalize
4. Adjudicate
5. Export

Do not turn internal substeps into a sprawling public stage taxonomy.

## Non-Negotiable v1 Rules

1. Models analyzing evidence must not see each other's outputs.
2. Every material recommendation must cite claim IDs.
3. Every cited claim must map to evidence IDs and source records.
4. Routing decisions must be deterministic in code, even when dispute classification is LLM-assisted.
5. A failed run with a rich partial trace is better than a polished but ungrounded report.
6. V1 consumes upstream evidence; it does not rebuild a competing retrieval stack.

## Implementation Order

Build in this order:

1. typed schemas and trace
2. `pyproject.toml`, per-project `.venv`, `config/config.yaml`, `prompts/`, and a canonical review notebook
3. evidence-ingest adapters for upstream bundles
4. one grounded analyst over imported evidence
5. three independent analysts
6. claim extraction and ledger build
7. dispute detection and routing
8. narrow factual and interpretive verification
9. synthesis and export for human review and downstream handoff
10. only then consider user steering, smarter stopping, and richer runtime checks

## Documentation To Read First

1. `CLAUDE.md`
2. `docs/adr/0001-adjudication-first-scope.md`
3. `docs/adr/0002-approved-external-reuse-strategy.md`
4. `docs/PLAN.md`
5. `docs/ARCHITECTURE_ONE_PAGE.md`
6. `docs/V1_IMPLEMENTATION_BRIEF.md`
7. `docs/SCOPE_MATRIX_V2.md`
8. `docs/notebooks/01_adjudication_review_journey.ipynb`
