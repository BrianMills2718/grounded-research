# Implementation Plans

`docs/PLAN.md` is the canonical execution plan for this project.

This directory is the numbered-plan surface for concrete implementation work
items once they begin. It does not replace or compete with `docs/PLAN.md`.

Use this directory only for scoped work items that need their own execution
plan. Broad project sequencing, scope, and acceptance criteria stay in
`docs/PLAN.md`.

## Gap Summary

| Gap | Title | Priority | Status | Blocks |
|---|---|---|---|---|
| — | No active implementation plans | — | — | — |

## Creating A New Plan

1. Copy `TEMPLATE.md` to `NN_name.md`
2. Fill in gap, steps, required tests
3. Add to this index
4. Commit with `[Plan #N]` prefix

## When To Use This Directory

- use `docs/PLAN.md` for repo-level direction and milestone sequencing
- use `docs/plans/NN_name.md` when a concrete work item needs its own file-level
  plan, tests, and blockers
- no numbered plans is a valid state while the project is still refining top-level
  documentation and scope

## Trivial Changes

Not everything needs a plan. Use `[Trivial]` for:
- Less than 20 lines changed
- No changes to `src/` (production code)
- No new files created
