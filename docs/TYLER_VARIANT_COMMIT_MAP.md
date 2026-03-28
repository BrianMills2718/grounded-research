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

## Policy

If an older tuned variant is worth preserving, preserve it by:

1. commit reference
2. benchmark artifact reference
3. explicit eval-time condition in `prompt_eval`

Do not preserve it by keeping a second co-equal runtime path in `main`.
