# Tyler Variant Commit Map

This note preserves the main historical runtime/prompt variants so the repo can
move aggressively toward the Tyler-literal path without keeping multiple
co-equal runtimes alive in `main`.

## Canonical Direction

- default runtime target: Tyler-literal
- legacy/calibrated variants: archived reference only
- comparison work: `prompt_eval` or benchmark harnesses, not alternate
  production runtime modes

## Key Historical Anchors

### Pre-Tyler calibrated / dense-dedup path

- `1aad652` Close post-Wave-2 hardening with dense UBI rerun
- `a40ed8f` Close Tyler local recovery wave with v8 results

Use when you need:

- the saved dense-dedup benchmark anchor
- the strongest pre-literal calibrated report behavior for comparison

### Tyler literal contract migration

- `012fd13` Start Tyler literal parity refactor with exact schema contract
- `c7bbca5` Migrate Stage 1 runtime to Tyler artifacts
- `0d4f8a1` Migrate Stage 2 runtime to Tyler artifacts
- `0492f81` Migrate Stage 3 runtime to Tyler artifacts
- `9d91d90` Migrate runtime Stage 4 to Tyler literal artifact
- `28d9fef` Migrate runtime Stage 5 and Stage 6 to Tyler artifacts
- `61eb1fe` Complete Tyler runtime parity migration

Use when you need:

- the first fully Tyler-native runtime state
- a baseline for adapter-deletion work

### Tyler prompt-quality recovery

- `71a6612` Plan Tyler Stage 3 role recovery and align defaults
- `e11a852` Repair underfilled Tyler Stage 6 decision fields
- `a40ed8f` Close Tyler local recovery wave with v8 results

Use when you need:

- the recovered Tyler-native path that beats cached Perplexity on tracked UBI

### Tyler canonical export cutover

- `683660e` Clarify 24h execution expectation and export deletion phases
- `cda75c7` Delete legacy export runtime path
- `ac78c5c` Remove legacy export adapter debt

Use when you need:

- the first `main` state with one Tyler-native export contract
- the commit boundary where legacy structured report and handoff surfaces were removed

### Stage 4/5 projection deletion

- `d42f5f5` Record canonical export contract and next cutover wave
- `9a79a5f` Delete Stage 4/5 compatibility ledger projections

Use when you need:

- the documented boundary where export deletion closed and the next child wave opened
- the commit boundary where the ignored Stage 4 compatibility return and dead
  Stage 5 current-ledger adapter were removed

### Stage 1/3 live runtime projection cutover

- `754f6f8` Clarify Stage 1/3 cutover phases and rollback policy
- `96bff31` Make Stage 2 consume Tyler Stage 1 directly
- `05304e0` Make legacy decomposition explicit-only in fixture mode
- `c81f20b` Replace runtime AnalystRun state with Stage 3 attempt traces
- `332827f` Prove Stage 4 live path runs from Tyler Stage 3 inputs
- `ba1c449` Remove live QuestionDecomposition dependency from runtime

Use when you need:

- the boundary where Stage 1/3 projections stopped participating in the live runtime
- the first `main` state where the engine consumes Tyler Stage 1/2/3 directly

### Isolated compatibility helper deletion

- `f90b718` Delete current-shape Stage 1 runtime entrypoints
- `32b4433` Delete legacy AnalystRun execution path
- `926480e` Delete isolated Stage 3 compatibility helpers

Use when you need:

- the boundary where non-live Stage 1/3 compatibility helper code disappeared
- the last commit range before the remaining current-shape model/helper surfaces
  became the only compatibility debt left in `main`

### Current-shape model surface deletion

- `dfa85dd` Validate Tyler Stage 1 without current-shape adapters
- `a9f31ee` Delete legacy verification and anonymization helpers
- `4e2ea43` Delete current-shape model classes

Use when you need:

- the boundary where `QuestionDecomposition`, `AnalystRun`, and `ClaimLedger`
  disappeared from `models.py`
- the first `main` state where the Stage 3 quality floor lives only on
  canonical Tyler `AnalysisObject`s

### Final Stage 5 and Stage 3/4 protocol deletion

- `fe31e8b` Delete Stage 5 compatibility protocol surfaces
- `ecfbce9` Delete Stage 3/4 compatibility protocol surfaces

Use when you need:

- the boundary where the last live current-shape verification protocol types
  disappeared from `main`
- the first `main` state where Stage 4 and Stage 5 operate only on Tyler-native
  semantic models

### Frozen shared-eval comparison

- `abb8765` Plan Tyler literal default evaluation wave
- `3d87f9c` Add frozen Tyler variant evaluation harness

Use when you need:

- the first disciplined `prompt_eval`-based comparison between Tyler-literal
  and the archived calibrated legacy anchor
- the manifest and script that compare saved artifacts without reviving a
  second runtime path

## Policy

If an older tuned variant is worth preserving, preserve it by:

1. commit reference
2. benchmark artifact reference
3. explicit eval-time condition in `prompt_eval`

Do not preserve it by keeping a second co-equal runtime path in `main`.
