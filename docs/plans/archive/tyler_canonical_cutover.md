# Tyler Canonical Cutover

**Status:** Completed (repo-local)
**Purpose:** Remove the remaining compatibility/runtime adapter debt and make
the Tyler-literal path the only canonical runtime in `grounded-research`.

## Why This Plan Existed

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

Completed result:

- repo-local compatibility/runtime adapter debt is no longer part of the live
  Tyler path
- `main` now keeps one canonical Tyler-literal runtime/export contract
- historical variants are preserved by commit references and benchmark/eval
  artifacts rather than co-equal runtime modes

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

Completed since the original write-up:

- Stage 1/3 runtime projections no longer drive collection, fixture loading, or
  human-readable phase summaries
- `PipelineState` no longer stores `analyst_runs`; it stores only canonical
  Tyler Stage 3 results plus `stage3_attempts`

Completed child waves:

- `docs/plans/isolated_compatibility_surface_deletion.md`

Completed child waves:

- `docs/plans/current_shape_model_surface_deletion.md`
- `docs/plans/stage5_internal_protocol_literalization.md`
- `docs/plans/stage34_compatibility_protocol_deletion.md`

## Next 24 Hours

The remaining wave is now narrow enough to execute as four ordered phases.
These phases are intended to run continuously in order unless a documented
architectural concern or failing verification result blocks the next slice.

### Phase A: Canonical Output Cutover

Goal:

- make Tyler Stage 6 and Tyler-native handoff artifacts the primary exported
  machine-readable outputs

Required changes:

- stop treating `FinalReport` as the primary canonical export artifact in the
  normal pipeline path
- add a Tyler-native downstream handoff artifact
- make `report.md`, `summary.md`, `trace.json`, and `handoff.json` derive
  primarily from Tyler Stage 5/6 artifacts

Acceptance:

- engine no longer needs `state.report` for the canonical successful path
- `handoff.json` is Tyler-native when Tyler Stage 5/6 exist
- export and phase-boundary tests pass

Completed:

- canonical successful runs no longer generate or store `FinalReport`
- `handoff.json` now prefers a Tyler-native downstream artifact built from
  Stage 2, Stage 5, and Stage 6
- `report.md` / `summary.md` / `handoff.json` now derive primarily from
  Tyler-native export artifacts in the successful path

### Phase B: Canonical Export Contract Rewrite

Goal:

- rewrite docs/tests so the primary export contract is Tyler-native

Required changes:

- update `docs/CONTRACTS.md`, `docs/PLAN.md`, `README.md`, and any primary
  boundary tests that still describe `FinalReport` as the main success artifact
- move compatibility `FinalReport` language behind an explicit compatibility note

Acceptance:

- active docs describe Tyler Stage 6 + Tyler handoff as the canonical output surface
- primary boundary tests assert Tyler-native artifacts first

Completed:

- README, PLAN, CONTRACTS, ARCHITECTURE, and FEATURE_STATUS now describe the
  Tyler-native output contract as canonical
- phase-boundary tests now assert Tyler Stage 5/6 first and explicitly skip
  legacy traces that predate Tyler-native export persistence

### Phase C: Stage 5 Compatibility Demotion

Goal:

- keep Stage 5 compatibility ledger only as transitional debt, not the primary
  semantic output of adjudication

Required changes:

- reduce live dependence on projected `ClaimLedger` where Stage 5 Tyler artifacts
  already contain the needed truth
- document and isolate any remaining consumer that still truly needs the
  compatibility ledger

Acceptance:

- no primary export or validation path depends on `ClaimLedger`
- remaining `ClaimLedger` usage is documented as transitional only

Current concern:

- removing `ClaimLedger` entirely from persisted state would require either
  a fresh Tyler-native trace fixture or a larger phase-boundary test rewrite
  to avoid turning broad contract coverage into pure skips
- that is a real cutover concern, not a reason to restore `ClaimLedger` as a
  canonical surface

Completed in this wave:

- canonical successful export no longer stores `FinalReport` in the live engine path
- `PipelineState` no longer stores a `report` field at all
- `handoff.json` now prefers the Tyler-native Stage 2/5/6 handoff artifact
- `verify_disputes_tyler_v1()` no longer depends on projected `ClaimLedger`
- the live engine now drives user steering and adjudication summaries directly
  from Tyler Stage 4/5 artifacts instead of the compatibility ledger
- phase-boundary tests now load the Tyler-native trace directly and rebuild the
  Stage 3 analyst boundary view from canonical Tyler artifacts instead of
  trusting stale projected `analyst_runs`
- docs now describe `FinalReport`, `DownstreamHandoff`, and projected
  `ClaimLedger` as compatibility debt rather than co-equal outputs

### Phase D: State Cleanup And Final Review

Goal:

- make the remaining compatibility fields in `PipelineState` explicit debt, not
  ambiguous co-equal outputs

Required changes:

- update `PipelineState` docs/comments and any remaining tests/docs that imply
  compatibility fields are first-class canonical outputs
- record any unresolved consumer dependency explicitly

Acceptance:

- the repo has one clear canonical runtime path and one clear compatibility-debt story
- remaining uncertainties are documented explicitly in repo docs, not left implicit

Remaining ordered phases after this commit:

1. remove the remaining live Stage 4/5 `ClaimLedger` projection debt from the
   runtime path
2. define and execute the Stage 1/3 runtime cutover away from
   `QuestionDecomposition` and `AnalystRun`
3. rerun the Tyler-native canonical benchmark/export path after the remaining
   runtime projection cleanup

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
