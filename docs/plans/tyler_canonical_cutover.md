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

Current highest-value remaining debt:

- Tyler Stage 3 still projects `AnalysisObject` into `AnalystRun` in the live path
- Tyler Stage 4/5/6 still project into `ClaimLedger` / `FinalReport`
- `PipelineState` still stores compatibility artifacts as first-class siblings of
  the Tyler-native stage artifacts

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

Completed:

- `50d73e2` removed live Stage 1 reconstruction from legacy
  `QuestionDecomposition`
- the canonical runtime now regenerates Tyler Stage 1 from the original
  question when the persisted Tyler artifact is absent

### Slice 2: Tighten canonical docs and public contract language

Files:

- `docs/CONTRACTS.md`
- `docs/DOMAIN_MODEL.md`
- `docs/ARCHITECTURE_ONE_PAGE.md`
- `docs/PLAN.md`

Rules:

- stop describing compatibility surfaces as the safer long-term contract
- mark adapters as temporary and slated for removal

Completed:

- `16b9aca` updated the active authority docs so Tyler-literal artifacts are the
  target canonical contract and compatibility surfaces are temporary migration debt

### Slice 2b: Kill Stage 2 reconstruction from legacy EvidenceBundle

Files:

- `engine.py`
- `src/grounded_research/verify.py`
- `src/grounded_research/export.py`

Rules:

- Stage 5 and Stage 6 must require canonical Tyler Stage 2
- do not rebuild Tyler Stage 2 from `EvidenceBundle` inside verification or synthesis
- fixture CLI should prefer persisted `tyler_stage_1.json` / `tyler_stage_2.json`
  artifacts when present

Acceptance:

- targeted tests pass
- verification and synthesis fail loud if canonical Tyler Stage 2 is absent
- fixture mode prefers canonical Tyler artifacts over legacy auto-detected files

Completed:

- `verify_disputes_tyler_v1()` now requires canonical Tyler Stage 2 instead of
  rebuilding it from `EvidenceBundle`
- `generate_tyler_synthesis_report()` now requires `state.tyler_stage_2_result`
- fixture CLI auto-detect now loads `tyler_stage_1.json` and `tyler_stage_2.json`
  from the fixture directory when available

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

Completed so far:

- canonical Stage 4 now prefers persisted Tyler Stage 3 `AnalysisObject`s plus
  the Tyler alias mapping instead of rebuilding its primary input from projected
  `AnalystRun`s
- the Stage 4 compatibility ledger projection now derives raw-claim provenance
  from Tyler Stage 3 claims rather than from projected `AnalystRun` claims
- export validation and `summary.md` now treat Tyler Stage 6 as the primary
  validated/rendered summary surface instead of the projected `FinalReport`

Still remaining in this slice:

- Stage 5 still projects `VerificationResult` into `ClaimLedger`
- `PipelineState` still stores compatibility artifacts as first-class siblings
  of the Tyler-native outputs

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

Completed:

- successful `AnalystRun` artifacts now require:
  - no error
  - at least one recommendation
  - at least one counterargument
  - at least one claim, with depth-specific minimums from config
  - non-empty claim evidence IDs
  - non-empty counterargument evidence IDs
- defaults are now config-backed under `analyst_success`

Explicit remaining nuance:

- full evidence-reference resolution against the active `EvidenceBundle` is still
  enforced at the stage boundary and Tyler-native runtime path, not inside the
  standalone `AnalystRun` model validator

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| old fixture path breaks immediately | fixture relies on `decomposition.json` projection only | require Tyler Stage 1 artifact or regenerate Stage 1 from the original question; do not restore old adapter path |
| deletion exposes a downstream consumer still reading old shapes | tests or CLI fail on removed `FinalReport`/`ClaimLedger` assumptions | move that consumer to Tyler-native artifacts or isolate it as a temporary adapter with an explicit removal follow-up |
| runtime/eval boundaries blur again | new config flags try to revive co-equal legacy runtime behavior | reject the change; move comparison work into `prompt_eval` |
