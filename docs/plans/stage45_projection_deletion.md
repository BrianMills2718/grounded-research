# Stage 4/5 Projection Deletion

**Status:** Completed
**Purpose:** Remove the remaining live `ClaimLedger` compatibility projections
from the Tyler-native runtime path so Stage 4 and Stage 5 expose only canonical
Tyler artifacts in `main`.

## Why This Plan Exists

The export layer is now Tyler-native, but one internal compatibility seam still
exists:

- `canonicalize_tyler_v1()` returns a projected `ClaimLedger` alongside the
  canonical Tyler Stage 4 artifact
- `engine.py` still unpacks that compatibility return even though it ignores it
- `tyler_stage5_to_current_ledger()` and its tests remain in the repo even
  though the live Stage 5 path no longer uses them

That leaves unnecessary ambiguity for coding agents about whether `ClaimLedger`
is still a real runtime output or only an archived/internal adapter.

## Canonical Decisions

1. Tyler Stage 4 returns only `ClaimExtractionResult` in the live runtime path.
2. Tyler Stage 5 returns only `VerificationResult` in the live runtime path.
3. Compatibility `ClaimLedger` projection helpers may exist only where an
   active consumer still requires them.
4. If no active consumer remains, delete the projection rather than hiding it
   behind config.

## Scope

This wave:

- removes the Stage 4 compatibility ledger return from the live runtime path
- deletes the unused Stage 5 `ClaimLedger` projection helper and its tests
- rewrites active docs to say exactly what remains

This wave does **not**:

- delete `ClaimLedger` as a model type yet
- delete `AnalystRun` compatibility projections yet
- rewrite historical docs outside the active authority surface

## Acceptance Criteria

This wave is complete only if:

1. `canonicalize_tyler_v1()` returns only the canonical Tyler Stage 4 artifact
2. `engine.py` no longer unpacks or ignores a compatibility ledger return
3. `tyler_stage5_to_current_ledger()` and compatibility-only Stage 5 adapter
   tests are deleted if they have no active runtime consumer
4. targeted canonicalize/verify/phase-boundary/adapter tests pass
5. active docs describe `ClaimLedger` projection debt precisely and narrowly

Completed result:

- `cda75c7` removed the live legacy export/runtime path
- `ac78c5c` removed the remaining legacy export adapter debt
- `9a79a5f` removed the ignored Stage 4 compatibility return and the dead
  Stage 5 current-ledger adapter
- this wave removed the ignored Stage 4 compatibility ledger return and the
  dead Stage 5 current-ledger adapter
- targeted suites passed after the cut:
  - `52 passed` across canonicalize, verify, adapter, and phase-boundary coverage

## Ordered Phases

### Phase 1: Remove Stage 4 compatibility return

- change `canonicalize_tyler_v1()` to return only the normalized Tyler Stage 4 result
- remove ignored `_compat_ledger` unpacking in `engine.py`
- update `tests/test_canonicalize.py`

Verification:

- `python -m py_compile src/grounded_research/canonicalize.py engine.py tests/test_canonicalize.py`
- `./.venv/bin/python -m pytest tests/test_canonicalize.py tests/test_phase_boundaries.py -q`

### Phase 2: Delete dead Stage 5 ledger adapter

- remove `tyler_stage5_to_current_ledger()` if no active runtime consumer remains
- remove its import from `verify.py`
- trim `tests/test_tyler_v1_stage5_6_adapters.py`

Verification:

- `python -m py_compile src/grounded_research/verify.py src/grounded_research/tyler_v1_adapters.py tests/test_tyler_v1_stage5_6_adapters.py`
- `./.venv/bin/python -m pytest tests/test_verify.py tests/test_tyler_v1_stage5_6_adapters.py -q`

### Phase 3: Rewrite active docs and commit map

- update:
  - `docs/CONTRACTS.md`
  - `docs/PLAN.md`
  - `docs/ROADMAP.md`
  - `docs/ARCHITECTURE_ONE_PAGE.md`
  - `docs/TYLER_LITERAL_PARITY_AUDIT.md`
  - `docs/TYLER_VARIANT_COMMIT_MAP.md`
  - `docs/plans/CLAUDE.md`
- record this wave’s commits and the new remaining stop line

Verification:

- `rg -n "ClaimLedger projection|compatibility ledger|tyler_stage5_to_current_ledger|_compat_ledger" docs src/grounded_research tests -g '!output/**'`
- any remaining hits in active docs must describe explicit remaining debt only

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| a live consumer still needs the Stage 4 projected ledger | engine or boundary tests fail after signature change | convert that consumer to Tyler Stage 4 directly; do not restore the compatibility return as default |
| Stage 5 adapter deletion breaks non-export tests | adapter tests fail because hidden runtime dependency still exists | either move that runtime dependency to Tyler Stage 5 directly or keep the adapter with a named, explicit consumer note |
| docs overstate completion | active docs claim `ClaimLedger` is gone everywhere when Stage 4 projection still exists elsewhere | narrow the language to “live export path removed; remaining internal adapter debt documented” |
