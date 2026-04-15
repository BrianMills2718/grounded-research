# Tyler Cross-Repo Handoff (2026-04-14)

This is the durable handoff for the Tyler-implementation and review program
across the repos that materially participated in it.

Scope:

- `grounded-research`
- `llm_client`
- `open_web_retrieval`
- `prompt_eval`
- `enforced-planning`

This is not a full ecosystem backlog. It is the handoff for the Tyler fidelity,
review, shared-infra, and documentation-governance work.

## Read This First

For current Tyler truth in `grounded-research`, read in this order:

1. `docs/TYLER_EXECUTION_STATUS.md`
2. `docs/TYLER_SPEC_GAP_LEDGER.md`
3. `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md`
4. `docs/TYLER_SYSTEMATIC_REVIEW_MATRIX.md`

If any older Tyler summary doc conflicts with those files, trust those four.

## Executive Status

### Tyler implementation status

- The audited local Tyler packet scope is closed in `grounded-research`.
- There are no active local Tyler implementation gaps.
- The only Tyler item still open is an operational watch on frontier-model
  variability, with an explicit reopen threshold.

### Cross-repo status

- `llm_client`: Tyler-relevant Gemini strict-schema and exact model-version work
  landed on `main`.
- `open_web_retrieval`: Tyler-relevant retrieval controls, Tavily parity, and
  Exa retrieval-instruction support landed on `main`.
- `prompt_eval`: the current Tyler eval gate is satisfied at 3 matched frozen
  cases; no additional eval breadth is required right now.
- `enforced-planning`: the process-level follow-through is still unfinished.
  The main remaining ecosystem task is to encode the audit/governance lessons as
  reusable planning policy rather than leaving them repo-local.

## Local Checkout Snapshot At Handoff Time

This section describes the local working state as observed when this handoff was
written. It matters because not every checkout is on the canonical branch.

| Repo | Local branch | Working tree | Ahead/behind | Meaning |
|---|---|---:|---:|---|
| `grounded-research` | `main` | clean | `0/0` | Safe current truth surface |
| `llm_client` | `fix/instructor-retry-unwrapping` | clean | `ahead 2` | Current checkout is on an unrelated branch; Tyler canonical state is on `main` |
| `open_web_retrieval` | `main` | clean | `ahead 2` | Current checkout includes unrelated unpublished metadata commits |
| `prompt_eval` | `main` | dirty (`docs/plans/01_master-roadmap.md`) | `0/0` | Pre-existing local edit; do not overwrite blindly |
| `enforced-planning` | `main` | dirty (`docs/ops/ECOSYSTEM_STATUS.md`, `FRICTION.md`) | `ahead 2` | Pre-existing local state; use a clean worktree before policy follow-through |

## Repo-By-Repo Handoff

### 1. grounded-research

#### Current truth

- Tyler implementation work is complete for the audited local packet scope.
- The canonical audit/review surfaces are complete and current:
  - `docs/TYLER_EXECUTION_STATUS.md`
  - `docs/TYLER_SPEC_GAP_LEDGER.md`
  - `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md`
  - `docs/TYLER_SYSTEMATIC_REVIEW_MATRIX.md`
- A durable example Tyler-shaped `trace.json` artifact exists:
  - `output/tyler_pipeline_state_trace_contract_reprojection_palantir/trace.json`

#### Unfinished work

There is no active local Tyler code-remediation lane.

The remaining `grounded-research` work is documentation consolidation and
operational monitoring:

1. **Doc truth cleanup**
   - Fix stale current-state language in:
     - `README.md`
     - `docs/ROADMAP.md`
     - `docs/TYLER_V1_CURRENT_REPO_MAP.md`
   - Demote or archive materially stale historical Tyler summaries:
     - `docs/TYLER_FINAL_COMPLIANCE_AUDIT.md`
     - `docs/TYLER_V1_DELIVERY_SUMMARY.md`
     - `docs/TYLER_LITERAL_PARITY_AUDIT.md`
     - `docs/TYLER_LITERAL_PROMPT_FIDELITY_AUDIT.md`

2. **Doc consolidation**
   - Keep the canonical Tyler current-state surface small:
     - `TYLER_EXECUTION_STATUS`
     - `TYLER_SPEC_GAP_LEDGER`
     - `TYLER_FULL_SPEC_AUDIT_MATRIX`
     - `TYLER_SYSTEMATIC_REVIEW_MATRIX`
   - Reduce `PLAN.md` and `ROADMAP.md` historical clutter.

3. **Operational watch**
   - Monitor `STATUS-FRONTIER-RUNTIME-001`
   - Reopen only if the threshold in
     `docs/plans/tyler_frontier_model_policy_wave1.md` is crossed.

#### Do not do

- Do not reopen solved Tyler remediation rows.
- Do not add new local runtime branches to chase shared-infra concerns.
- Do not treat broader frozen-eval expansion as the default next blocker.

#### Recommended next step in this repo

- Run a docs-only consolidation wave, not a new Tyler runtime wave.

### 2. llm_client

#### Current truth

Tyler-relevant shared-runtime work is landed on `main`:

- Gemini strict-schema study and direct-Gemini thinking-budget fix
- exact shared registry parity for
  `openrouter/google/gemini-3.1-pro-preview`

For Tyler work, `main` is the canonical branch, not the current local
`fix/instructor-retry-unwrapping` checkout.

#### Unfinished work

No active Tyler-specific blocker remains in `llm_client`.

What remains is ecosystem or repo-level follow-through:

1. **Shared behavior-verification infrastructure**
   - `llm_client` is still one of the natural homes for shared runtime event
     logging helpers and reusable trace evidence utilities.
   - This is not required to close Tyler, but it is required to avoid repeating
     Tyler's audit failure pattern elsewhere.

2. **Normal repo-local backlog**
   - `docs/plans/CLAUDE.md` shows one active unrelated plan:
     - Plan 91 `Pending-Atom Submit Churn Requires TODO Progress`
   - That plan is not part of Tyler closure and should not be mixed into the
     Tyler handoff.

#### Local checkout caution

- Current branch: `fix/instructor-retry-unwrapping`
- Ahead by 2 commits
- Do not start Tyler-related `llm_client` work from this branch unless the goal
  is explicitly to continue that unrelated branch.
- Switch to `main` or use a fresh worktree before any new Tyler-adjacent shared
  runtime work.

### 3. open_web_retrieval

#### Current truth

Tyler-relevant shared retrieval work is landed:

- Tavily direct adapter parity
- Exa direct adapter parity
- typed retrieval controls
- generic `retrieval_instruction`
- adapter request-body verification

The canonical statement is in:

- `docs/ROADMAP.md`

#### Unfinished work

No Tyler-specific blocker remains in `open_web_retrieval`.

Open shared-library work:

1. **Consumer-proven contract expansion only**
   - Add new retrieval controls only when a real consumer can prove it needs
     them.
   - Keep the boundary generic; do not add Tyler-specific knobs.

2. **v1.0 shareable-library gate**
   - Still open in `docs/ROADMAP.md`
   - Not a Tyler blocker

#### Local checkout caution

- Current branch: `main`
- Ahead by 2 commits
- Those unpublished commits are unrelated metadata work (`Plan #179` / goal
  metadata annotations), not Tyler closure work.
- Do not intermingle handoff or Tyler follow-through with those commits without
  checking intent first.

### 4. prompt_eval

#### Current truth

The current Tyler eval gate is satisfied:

- UBI matched pair scored
- PFAS matched pair scored
- LLM SWE matched pair scored

For the current lane, this is enough. `prompt_eval` is no longer the default
next task unless a new implementation wave needs regression checking or a new
prompt/model comparison question appears.

#### Unfinished work

No current Tyler-required work is open in `prompt_eval`.

Optional future uses:

1. add more frozen Tyler-vs-legacy cases only if a later change needs broader
   regression coverage
2. use `prompt_eval` for future prompt/model/export comparisons before opening
   new local experimentation inside `grounded-research`

#### Local checkout caution

- Current branch: `main`
- Working tree is dirty:
  - `docs/plans/01_master-roadmap.md`
- This is pre-existing local state. Clean or branch around it before doing any
  future Tyler-related `prompt_eval` work.

### 5. enforced-planning

#### Current truth

This repo still lacks the fully generalized process-level follow-through from
the Tyler audit.

The Tyler review proved several reusable governance rules that should not stay
trapped in `grounded-research` docs:

1. contract migration/cutover can complete while spec compliance is still false
2. structure claims and behavior claims need different evidence
3. behavior claims require runtime evidence, not only static review
4. external-spec work should use a clause/unit ledger or equivalent
5. summary docs must not outrun the current ledger/status surface

#### Unfinished work

This is the most important remaining ecosystem follow-through.

Recommended work items:

1. **Add a reusable spec-gap-ledger pattern**
   - per-clause review units
   - evidence type
   - classification
   - owner
   - next action

2. **Add structure-vs-behavior claim governance**
   - structure claims can close on static evidence
   - behavior claims require runtime evidence

3. **Add the migration-vs-compliance rule**
   - completing a contract migration is not enough to claim full compliance

4. **Tie runtime evidence to shared infrastructure**
   - this should align with the planned `trace_eval` direction rather than stay
     repo-local forever

#### Local checkout caution

- Current branch: `main`
- Ahead by 2 commits
- Dirty:
  - `docs/ops/ECOSYSTEM_STATUS.md`
  - `FRICTION.md`
- Do not start this governance follow-through on the dirty checkout. Use a
  clean worktree.

## Relevant Non-Repo Dependency

### trace_eval

`trace_eval` is still planned rather than created.

This matters because the Tyler audit exposed a shared need for:

- trace-based behavior assertions
- event-order verification
- value-propagation verification
- reusable runtime evidence checks

Until `trace_eval` exists, behavior-verification logic will continue to live
inside producing repos.

## What Is Actually Unfinished

If a new agent resumes this work, the real unfinished set is:

1. `grounded-research` doc-truth and doc-consolidation cleanup
2. `enforced-planning` process/governance follow-through
3. eventual `trace_eval` shared verification infrastructure

Everything else is either:

- already landed,
- optional future follow-through,
- or a watch item rather than an active implementation gap.

## Suggested Restart Order

1. Clean up stale current-state docs in `grounded-research`
2. Archive or hard-deprecate the stale historical Tyler summary docs
3. Open a clean `enforced-planning` worktree and upstream the Tyler audit
   governance rules
4. Only then consider a dedicated `trace_eval` repo/program

## Questions To Re-Ask Before New Work

If new work begins later, re-check these before editing:

1. Is the task Tyler-required, or merely useful?
2. Is the work local to `grounded-research`, or should it live in shared infra?
3. Is the open issue a real implementation gap, or only a documentation or
   operational-watch item?
4. Is the local checkout clean, or is there pre-existing dirt that requires a
   fresh worktree?
