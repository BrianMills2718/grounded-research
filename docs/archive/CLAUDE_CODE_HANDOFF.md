# Claude Code Handoff

This file is the disk-backed session handoff for the next Claude Code run.
It summarizes the current plan state, the durable artifacts that were updated,
and the remaining decisions that still need closure.

## Read First

1. [`CLAUDE.md`](../CLAUDE.md)
2. [`docs/PLAN.md`](./PLAN.md)
3. [`docs/UNCERTAINTIES.md`](./UNCERTAINTIES.md)
4. [`docs/adr/0004-agentic-verification-and-fail-loud-phase4.md`](./adr/0004-agentic-verification-and-fail-loud-phase4.md)
5. [`docs/plans/01_draft-implementation-adoption.md`](./plans/01_draft-implementation-adoption.md)
6. [`scripts/relationships.yaml`](../scripts/relationships.yaml)

## Current State

- The repo is adjudication-first and the canonical execution plan stays in
  [`docs/PLAN.md`](./PLAN.md).
- Phase 4 is currently defined as the structured v1 slice:
  `Phase 4a` query generation plus `Phase 4b` structured arbitration.
- The eventual single-loop agentic Phase 4 merge remains a future milestone,
  not the active v1 target.
- Phase 4 fail-loud rules are now persisted in ADR-0004, prompts, code, and the
  governance target.
- Governance now runs through [`scripts/ci_checks.py`](../scripts/ci_checks.py)
  and the GitHub Actions workflow in [`.github/workflows/governance.yml`](../.github/workflows/governance.yml).

## Updated Durables

- [`src/grounded_research/verify.py`](../src/grounded_research/verify.py)
- [`engine.py`](../engine.py)
- [`prompts/verification_queries.yaml`](../prompts/verification_queries.yaml)
- [`prompts/arbitration.yaml`](../prompts/arbitration.yaml)
- [`docs/PLAN.md`](./PLAN.md)
- [`docs/UNCERTAINTIES.md`](./UNCERTAINTIES.md)
- [`docs/adr/0004-agentic-verification-and-fail-loud-phase4.md`](./adr/0004-agentic-verification-and-fail-loud-phase4.md)
- [`scripts/check_adr_invariants.py`](../scripts/check_adr_invariants.py)
- [`scripts/ci_checks.py`](../scripts/ci_checks.py)
- [`.github/workflows/governance.yml`](../.github/workflows/governance.yml)

## Open Decisions

1. Adoption gate for the committed draft implementation surfaces.
2. Whether Phase 4 agentic merge becomes a separate future milestone or stays
   deferred behind the structured v1 contract.
3. Real baseline evidence and rubric for `Phase -1`.

## What To Do Next

1. Close the adoption gate in [`docs/plans/01_draft-implementation-adoption.md`](./plans/01_draft-implementation-adoption.md).
2. Decide whether the Phase 4 agentic merge gets its own milestone surface.
3. Add the real-source baseline evidence and explicit rubric for `Phase -1`.
4. Run the governance target if you want to validate the newly added checks:
   `python scripts/ci_checks.py`

## Notes

- No validation was run on the latest documentation/governance edits.
- The handoff file is meant to be read alongside the plan and uncertainties, not
  as a replacement for them.
