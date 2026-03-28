# Tyler Canonical Cutover

**Status:** In Progress
**Purpose:** Remove the remaining compatibility/runtime adapter debt and make
the Tyler-literal path the only canonical runtime in `grounded-research`.

## Why This Plan Exists

The repo now has Tyler-native Stage 1-6 runtime artifacts, but still keeps a
meaningful amount of migration scaffolding alive:

- old runtime artifacts still act as compatibility/public surfaces
- `tyler_v1_adapters.py` still projects between old and Tyler-native shapes
- parts of the runtime still rebuild Tyler artifacts from old shapes instead of
  requiring the canonical Tyler path

That is bad for coding-agent tractability. It creates two conceptual systems in
one codebase.

## Canonical Decisions

1. Tyler-literal is the only canonical runtime target.
2. Legacy/calibrated variants are preserved by commit references and eval-time
   comparisons, not as co-equal runtime modes.
3. Quality-first defaults win over cost-first defaults.
4. Strict analyst success policy should be configurable, but the default should
   be the highest-quality setting that is operationally reliable.
5. Compatibility adapters are temporary migration tools, not part of the
   desired architecture.

## Archived Variant References

See:

- `docs/TYLER_VARIANT_COMMIT_MAP.md`

## Scope

This cutover removes repo-local adapter/runtime debt in phases:

1. stop rebuilding Tyler Stage 1 from old decomposition artifacts in the live path
2. stop treating old compatibility projections as the safer external contract
3. remove Tyler-to-current and current-to-Tyler runtime projections that are no
   longer needed
4. tighten runtime success criteria and canonical docs around the single
   Tyler-literal path

This plan does **not**:

- rebuild shared-infra provider/model parity inside this repo
- keep a long-lived dual-runtime system in `main`

## Acceptance Criteria

This cutover is complete only if:

1. the live runtime no longer needs old decomposition artifacts to produce or
   consume Tyler Stage 1
2. the live runtime no longer silently reconstructs canonical Tyler artifacts
   from old compatibility surfaces when the canonical path should already exist
3. docs state one canonical contract and one canonical runtime path
4. any preserved legacy behavior lives only in commit history or eval-time
   comparisons

## Adapter Debt Inventory

Highest-value runtime debt:

- `src/grounded_research/tyler_v1_adapters.py`
- `engine.py` fallback from `QuestionDecomposition` -> Tyler Stage 1
- `canonicalize.py` fallback from `QuestionDecomposition` -> Tyler Stage 1
- `verify.py` fallback from `QuestionDecomposition` -> Tyler Stage 1
- `export.py` fallback from `QuestionDecomposition` -> Tyler Stage 1

Second-wave debt:

- Tyler -> current projections for `AnalystRun`, `ClaimLedger`, `FinalReport`
- old public/runtime docs still centered on compatibility artifacts

## Execution Order

### Slice 1: Kill Stage 1 regeneration from old decomposition

Files:

- `engine.py`
- `src/grounded_research/canonicalize.py`
- `src/grounded_research/verify.py`
- `src/grounded_research/export.py`

Rules:

- if Tyler Stage 1 is missing, regenerate it from the question, not from
  `QuestionDecomposition`
- do not use `current_decomposition_to_tyler()` in the live runtime path

Acceptance:

- targeted tests pass
- fixture and question paths still produce Tyler Stage 1 deterministically

### Slice 2: Tighten canonical docs and public contract language

Files:

- `docs/CONTRACTS.md`
- `docs/DOMAIN_MODEL.md`
- `docs/ARCHITECTURE_ONE_PAGE.md`
- `docs/PLAN.md`

Rules:

- stop describing compatibility surfaces as the safer long-term contract
- mark adapters as temporary and slated for removal

### Slice 3: Remove Tyler-to-current runtime projections where no longer needed

Likely files:

- `src/grounded_research/analysts.py`
- `src/grounded_research/canonicalize.py`
- `src/grounded_research/verify.py`
- `src/grounded_research/export.py`
- `src/grounded_research/models.py`
- `src/grounded_research/tyler_v1_adapters.py`

Acceptance:

- runtime no longer depends on projected `AnalystRun` / `ClaimLedger` /
  `FinalReport` as primary truth
- deleted code exceeds added code

### Slice 4: Strict analyst success defaults

Files:

- `src/grounded_research/models.py`
- `config/config.yaml`
- tests covering analyst success policy

Default policy should require:

- no error
- at least one recommendation
- at least one counterargument
- at least one claim
- evidence references resolve

Depth-specific minimum claim counts may remain configurable.

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| old fixture path breaks immediately | fixture relies on `decomposition.json` projection only | require Tyler Stage 1 artifact or regenerate Stage 1 from the original question; do not restore old adapter path |
| deletion exposes a downstream consumer still reading old shapes | tests or CLI fail on removed `FinalReport`/`ClaimLedger` assumptions | move that consumer to Tyler-native artifacts or isolate it as a temporary adapter with an explicit removal follow-up |
| runtime/eval boundaries blur again | new config flags try to revive co-equal legacy runtime behavior | reject the change; move comparison work into `prompt_eval` |
