# Tyler Shared Parity Closure Wave 1

**Status:** Active
**Type:** shared-infra closure
**Priority:** High
**Parent plan:** `docs/plans/tyler_faithful_execution_remainder.md`

## Goal

Close the remaining Tyler-required shared-runtime gaps that still block a
truthful "faithfully executed" claim after repo-local remediation is complete.

This wave is intentionally narrow. The frozen-eval gate is now satisfied for
the current implementation lane:

- UBI matched frozen case
- PFAS matched frozen case
- LLM SWE matched technical frozen case

That is enough directional evidence for current implementation work. Broader
eval expansion is no longer the active frontier unless a later regression wave
needs it.

## Scope

In scope:

- merge or land the shared `llm_client` Gemini strict-schema fix and study
- reconcile `grounded-research` status docs once that shared state is real
- keep frontier-runtime reliability explicitly tracked as an open shared issue

Out of scope:

- additional frozen-eval breadth for its own sake
- reopening local runtime branches in `grounded-research`
- new benchmark waves unless a later implementation slice needs them

## Pre-Made Decisions

1. `3` matched frozen cases is sufficient for the current eval gate.
2. Further frozen-eval breadth is deferred unless:
   - a new Tyler implementation wave needs regression coverage, or
   - a later result creates a material contradiction.
3. The next active Tyler work is shared-runtime closure, not more evaluation.
4. The first shared-runtime target is the `llm_client` Gemini strict-schema
   lane because the fix and evidence already exist on branch
   `gemini-schema-study`.
5. Frontier-runtime reliability remains explicitly open after this wave unless
   a separate shared plan closes it.

## Success Criteria

This wave passes only if:

1. `grounded-research` docs stop implying that broader eval breadth is the next
   default blocker,
2. the active frontier is clearly stated as shared-runtime/model parity,
3. the `llm_client` Gemini strict-schema lane is either merged or truthfully
   recorded as still pending with exact branch/commit ownership,
4. the repo leaves one explicit next Tyler-required shared item after this wave,
   not a vague list.

## Phases

### Phase 1: Reconcile Current Frontier

Deliverables:

- status docs that treat frozen eval as sufficient for now
- explicit statement that the next active lane is shared parity

### Phase 2: Land Gemini Shared Fix

Deliverables:

- shared `llm_client` branch merged or equivalently landed on the active shared
  branch
- focused verification on the landed shared runtime path

### Phase 3: Reconcile Ownership Docs

Deliverables:

- updated `docs/TYLER_EXECUTION_STATUS.md`
- updated `docs/TYLER_SHARED_INFRA_OWNERSHIP.md`
- updated `docs/plans/tyler_faithful_execution_remainder.md`

### Phase 4: Name The Next Remaining Shared Tyler Item

Deliverables:

- one explicit next active item after Gemini closure
- likely frontier-runtime reliability, unless the merge reveals a different
  higher-priority shared blocker

## Verification

Minimum verification:

1. doc grep shows no stale "eval breadth is the next default frontier" claim
2. `llm_client` focused tests pass on the landed Gemini shared path
3. `grounded-research` docs point to exact shared ownership truthfully

## Todo List

- [ ] Phase 1: reconcile current frontier
- [ ] Phase 2: land Gemini shared fix
- [ ] Phase 3: reconcile ownership docs
- [ ] Phase 4: name the next remaining shared Tyler item

## Current Status

As of 2026-04-09:

- the current eval gate is satisfied
- the Gemini strict-schema shared lane is now in review as `llm_client` PR #27
  (`gemini-schema-main-merge` at `e9a0cbf`)
- focused verification on that branch passed:
  - `20 passed, 228 deselected`

So the active remaining question after Gemini is no longer eval breadth. It is
which shared Tyler item is next if PR #27 merges cleanly.
