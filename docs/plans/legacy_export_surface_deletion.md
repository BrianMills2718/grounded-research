# Legacy Export Surface Deletion

**Status:** In Progress
**Purpose:** Delete compatibility-only export surfaces that no longer have live runtime consumers, so the repo has one canonical Tyler-native output contract and does not keep legacy report/handoff shapes alive in `main` just for tests.

## Why This Plan Exists

The live runtime no longer depends on:

- projected `FinalReport`
- stored `PipelineState.report`
- projected `ClaimLedger` for export validation
- projected `ClaimLedger` for live Stage 5 execution

What remains is compatibility-only debt:

- `generate_report()` and related grounding helpers
- `FinalReport`
- `DownstreamHandoff`
- legacy export tests that only prove the compatibility path
- `PipelineState.claim_ledger` as a stored trace field

Keeping those alive in `main` makes the contract ambiguous for coding agents.

## Canonical Decisions

1. Tyler Stage 6 `SynthesisReport` is the only canonical structured export artifact.
2. Tyler Stage 2/5/6 handoff is the only canonical machine-readable downstream artifact.
3. Legacy export/report surfaces are preserved by commit history, not as live runtime helpers.
4. Deleting compatibility-only code is preferred to isolating it behind more config or fallback branches.

## Scope

This wave deletes repo-local export compatibility surfaces only.

It does **not**:

- remove the `ClaimLedger` model class itself yet
- remove Stage 4/5 projection helpers from `tyler_v1_adapters.py` yet
- rewrite historical docs outside the active authority surface

## Acceptance Criteria

This wave is complete only if:

1. `PipelineState` no longer stores compatibility export artifacts (`claim_ledger`, `report`)
2. `export.py` no longer contains compatibility-only structured report generation/rendering helpers
3. `write_outputs()` only writes Tyler-native summary/handoff outputs
4. active docs describe one canonical export contract with no active ambiguity
5. targeted export/verify/prompt/boundary tests pass after compatibility-test removal or replacement

## Ordered Phases

### Phase 1: Delete stored compatibility export state
- remove `PipelineState.claim_ledger`
- keep old traces readable via Pydantic's default extra-ignore behavior
- acceptance: state/boundary suites still pass

### Phase 2: Delete compatibility export helpers
- remove from `export.py`:
  - `validate_grounding`
  - `_ensure_unresolved_disputes_in_report`
  - `generate_report`
  - `_render_structured_report`
  - legacy `DownstreamHandoff` fallback branch in `write_outputs()`
- remove dead imports tied only to those helpers
- acceptance: `export.py` still supports canonical Stage 6 rendering/writing only

### Phase 3: Delete compatibility export tests and adapter-only report projection tests
- remove tests that exist only to prove `FinalReport`/legacy handoff behavior
- keep tests that prove Tyler-native grounding, summary writing, and handoff behavior
- acceptance: remaining tests validate only the canonical path or explicitly retained adapters

### Phase 4: Rewrite active docs and commit map
- update active docs to remove live ambiguity about `FinalReport`/legacy handoff
- add this deletion wave to `TYLER_VARIANT_COMMIT_MAP.md`
- acceptance: active docs describe one canonical output contract and archived variant references

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| hidden live consumer still needs `claim_ledger` on `PipelineState` | engine or active tests fail after field removal | restore only the minimum local data flow needed for that consumer, or convert that consumer to Tyler-native artifacts immediately |
| export tests collapse because they only covered deleted compatibility code | large test loss with no canonical replacement | replace with Tyler-native assertions, do not restore compatibility helpers |
| docs drift into contradictory historical/current statements | active docs still describe `FinalReport` as live output | tighten only the active authority docs and leave archival docs labeled historical |
