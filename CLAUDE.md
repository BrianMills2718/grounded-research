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

Collection observability should use the shared `llm_client` `tool_calls`
surface. Search calls should flow through `open_web_retrieval` with the run
`trace_id` and collection task name. Project-local fetch wrappers may emit the
same shared `tool_calls` directly until the fetch path is migrated.

Search-provider adapters and provider-specific API clients belong in shared
infrastructure, not in this repo. If Tavily or Exa parity work is needed,
implement it in `open_web_retrieval` and import it here.

The `research_v3` -> `grounded-research` handoff path is valid and proven:
`research_v3` exports `EvidenceBundle` JSON and this repo accepts it via
`engine.py --fixture bundle.json`.

Gemini structured-output quality is not assumed to be neutral under strict JSON
Schema decoding. If Gemini is used in reasoning-critical structured stages,
compare schema-constrained mode against prompt-guided JSON mode and log the
result before standardizing on one path.

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

### 8a. One Canonical Runtime

This repo should converge toward:

- one canonical contract
- one canonical runtime path
- one default prompt family
- one default quality-first model policy

Do not keep co-equal "legacy" and "new" runtimes alive inside the main
execution path.

If historical tuned prompts or older behavior need to be preserved, keep them
as:

- archived commits documented in repo docs
- evaluation-only comparison conditions in `prompt_eval`

Do not turn them into long-lived alternate runtime modes unless the difference
is genuinely a narrow prompt/model policy knob and not a different contract or
control-flow path.

Compatibility adapters are temporary migration tools only. Remove them
aggressively once the Tyler-literal path is verified.

### 8b. Continuous Canonical Cutover

When an active cutover plan is in progress, do not stop after one narrow patch
just because one commit landed.

The expected behavior is:

- determine the remaining slices needed to finish the active cutover wave
- write those slices into the active plan and notebook before continuing
- execute them in order
- commit each verified slice immediately
- continue until the wave is actually complete

Stop only for:

- a real uncertainty about the desired architecture or contract
- a concrete concern that the next deletion would break an undeclared consumer
- a failing verification result that invalidates the current plan

If there is uncertainty, document it in the plan, notebook, and traceable repo
surface, then continue with the next unblocked slice. Do not stop simply
because the work is large or because multiple commits are needed.

### 8c. Next-24h Execution Expectation

When the user asks for the next 24 hours of work to be planned and executed,
the expected behavior is strict:

- determine every remaining phase needed to finish the active repo-local wave
- make the phases explicit in the active plan and notebook before continuing
- keep an explicit todo list synchronized with the active plan as phases move
  from pending -> in progress -> completed
- make acceptance criteria and failure modes explicit for each phase
- execute continuously through all planned phases
- commit every verified slice immediately
- push once the wave is complete or once a durable boundary is reached

Do not stop for:

- the size of the remaining work
- the fact that multiple commits are needed
- the existence of historical compatibility code that the plan already says to delete

Stop only for:

- a real architectural uncertainty not covered by the active plan
- a concrete undeclared consumer that would be broken by the next deletion
- a failing verification result that means the plan itself is wrong

If one of those happens, document it explicitly in the plan, notebook, and
authority docs, then continue with the next unblocked phase instead of leaving
the repo in a vague intermediate state.

Once the active repo-local wave is actually complete, stop opening new local
cleanup slices just to stay busy. Freeze `grounded-research` on the canonical
Tyler path, keep benchmark anchors stable, and move the next frontier into
`prompt_eval`, `llm_client`, or `open_web_retrieval` unless a new benchmark
creates a grounded-research-specific diagnosis.

When there is no active repo-local implementation wave, the next 24-hour plan
must be a cross-repo program with:

- a grounded-research plan and notebook that define the phases, success
  criteria, and evidence artifacts
- `prompt_eval` as the default place for comparing Tyler-literal against
  archived calibrated variants
- `llm_client` and `open_web_retrieval` as the default homes for any runtime,
  observability, provider, or retrieval follow-through exposed by that
  evaluation

Do not reopen deleted local compatibility code just to create another
comparison path. Use frozen artifacts, commit references, and shared eval
infrastructure instead.

When there *is* an active repo-local implementation wave, treat the request as
"finish the wave unless a real architectural concern appears." In practice this
means:

- convert the wave into explicit ordered phases with pass/fail criteria
- keep the plan's todo list synchronized as phases move from pending -> in
  progress -> completed
- do not stop after the audit, after the first patch, or after the first commit
- continue through every remaining phase until the wave is actually closed
- if a real uncertainty appears, record it in the active plan/notebook and
  authority docs, then continue with the next unblocked phase instead of
  pausing the entire program

The default assumption is not "plan a lot and stop." The default assumption is
"plan, execute, verify, commit, continue" until the current wave is done.

### 8d. Rollback Safety During Long Waves

When a long cutover or deletion wave is in progress, preserve rollback points
aggressively:

- every verified slice gets its own commit immediately
- commit before switching phases
- do not accumulate multiple verified deletions in one uncommitted batch
- if a cutover changes contracts, update the active plan before the next commit

The repo should always be recoverable to the last verified boundary by commit,
not by reconstructing partial work from conversation history.

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

### 13. Finish The Accepted Wave

Once a plan wave is accepted and its decisions are explicit enough to execute,
continue through that wave without pausing after each small slice.

Allowed stop conditions are narrow:

- the active wave is fully complete and verified
- a real blocker invalidates the plan
- a newly discovered constraint requires a plan update before safe execution
- the user redirects the work

If uncertainty appears inside an accepted wave, record it in the active plan,
trace, or tech-debt surface and continue unless it invalidates the current
implementation path.

### 14. Continuous Wave Execution

When a repo-local plan has pre-made decisions and acceptance criteria, execute
the full wave continuously. Do not stop after one commit, one patch, or one
test pass just because a local slice landed.

The default behavior in this repo is:

- finish the current gated wave end-to-end
- log uncertainties in the active plan, roadmap, or tech-debt surface
- continue to the next pre-made step immediately
- stop only for:
  - a real external blocker
  - a failed gate that changes the implementation decision
  - a user redirect

Do not create fake pause points. If the next step is already decided in the
plan, do it.

Benchmark-preservation waves are included in this rule. Do not stop after a
single rerender, a partial benchmark, or an intermediate comparison file. A
benchmark wave is only complete when the run, the comparison, the plan status,
and the roadmap state all agree on the result.

Long runtime is not, by itself, a blocker. If a benchmark or smoke run is
still executing and there is no concrete code-level failure, keep it running
until:

- it completes,
- it reaches the configured timeout boundary,
- or it emits a real error that changes the implementation decision.

If the change is architectural, update the relevant ADR before continuing.

When implementing against an accepted active plan, continue autonomously until
that plan's acceptance criteria are satisfied or a real blocker is reached.
Do not stop at a convenient intermediate slice just because one patch landed.
Do not stop after a single commit if the active plan still has open work.
Drive the current wave all the way to its acceptance gate in one session unless
you hit a real blocker, a destructive-action boundary, or an unplanned
architectural decision that the plan did not pre-make.
If a real uncertainty appears mid-run, document it in the active plan and
`docs/TECH_DEBT.md`, then keep moving on the remaining non-blocked work.

Treat long execution waves as continuous work, not as a sequence of
conversation-sized patches. If a next-24-hour plan exists, the default
behavior is to keep executing the full wave until every pre-made step is done
or a real blocker is hit. Do not pause merely because the work became slow,
large, or multi-commit.

For overnight-style benchmark and preservation waves, the expectation is
stronger:

- keep running until the active wave is either closed or replaced by a new
  benchmark-triggered plan
- if uncertainty appears, log it in the active plan and keep executing the
  remaining non-blocked steps
- do not stop at a completed run without also saving comparisons and updating
  the plan/index/roadmap state
- do not open speculative new work just to stay busy; close the current gate
  first

When the user explicitly asks for a next-24-hour or overnight closure wave, the
default expectation is strongest:

- determine the full set of remaining local phases first
- write or update the active plan and notebook before implementation
- execute every pre-made slice in order without pausing for conversational
  check-ins
- if one slice closes and the plan already names the next slice, continue
  immediately
- if uncertainty appears, record it in the active plan, roadmap, audit, or
  tech-debt surface and keep executing the remaining non-blocked slices
- stop only for a real external blocker, a failed gate that changes the plan,
  or explicit user redirect

Do not treat "one commit landed" as a stopping condition. Do not treat "the
benchmark ran once" as a stopping condition. Close the entire accepted wave.

### 15. Documentation Governance Is In Scope

This repo intentionally keeps a documentation-governance layer alongside the
core project docs.

Authority chain:

- `CLAUDE.md` is the canonical project operating guide
- `docs/PLAN.md` is the canonical execution plan
- `docs/plans/` holds per-task plan docs

Active implementation rule:

- `docs/plans/CLAUDE.md` must reflect the true active/completed plan set
- if a long-running execution wave is in progress, the agent should finish the
  wave rather than pause after each small step
- uncertainties belong in repo docs, not only in chat

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
12. user steering for preference/ambiguity disputes (implemented)
13. configurable depth modes and quality optimizations

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
- `docs/ROADMAP.md` — forward-looking priorities
- `docs/CONTRACTS.md` — inter-phase data flow contracts
- `docs/ARCHITECTURE_ONE_PAGE.md` — system boundary and runtime layers
- `docs/FEATURE_STATUS.md` — scorecard implementation tracking
- `docs/COMPETITIVE_ANALYSIS.md` — SOTA comparison results
- `docs/plans/v1_spec_alignment.md` — V1 spec gap analysis
- `docs/adr/` — architectural decision records
