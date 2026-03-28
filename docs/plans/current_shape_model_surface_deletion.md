# Current-Shape Model Surface Deletion

**Status:** Completed
**Purpose:** Delete the remaining current-shape model/helper surfaces so
`main` keeps one canonical Tyler-native runtime and one canonical vocabulary.

## Why This Plan Exists

The live runtime no longer executes through `QuestionDecomposition`,
`AnalystRun`, or `ClaimLedger`. After the isolated compatibility helper
deletions, what remains is a smaller but still confusing compatibility layer:

- Stage 1 validation still projects Tyler Stage 1 into `QuestionDecomposition`
- `verify.py` still exposes legacy `verify_disputes()`
- `canonicalize.py` still exposes legacy `build_ledger()`
- `anonymize.py` still exposes legacy `scrub_analyst_run()`
- current-shape adapter helpers and model classes still remain in `models.py`

This no longer protects the live system. It mainly keeps a second vocabulary
alive in `main` and makes the codebase harder for agents to reason about.

## Canonical Decisions

1. `main` keeps one canonical runtime contract: Tyler Stage 1-6 artifacts.
2. Older current-shape entities are preserved by commits and eval artifacts,
   not by keeping them runnable in `main`.
3. Tyler Stage 1 validation should operate directly on `DecompositionResult`,
   not through a projected `QuestionDecomposition`.
4. Legacy helper functions should be deleted before model classes.
5. If a test exists only to prove a removed compatibility surface, delete it
   or rewrite it against Tyler-native artifacts.

## Acceptance Criteria

This wave is complete only if:

1. `decompose.py` validates Tyler Stage 1 without building a live
   `QuestionDecomposition`
2. `verify.py` exposes only Tyler-native verification entrypoints in the live
   module surface
3. `canonicalize.py` no longer exposes `build_ledger()`
4. `anonymize.py` no longer exposes `scrub_analyst_run()`
5. `models.py` no longer defines `QuestionDecomposition`, `AnalystRun`, or
   `ClaimLedger`
6. targeted decomposition/verification/anonymization/phase-boundary tests pass
7. active docs describe the remaining compatibility policy truthfully and do
   not treat current-shape models as co-equal runtime contracts

## Completed

- `dfa85dd` Validate Tyler Stage 1 without current-shape adapters
- `a9f31ee` Delete legacy verification and anonymization helpers
- `4e2ea43` Delete current-shape model classes

Verified:

- `python -m py_compile src/grounded_research/decompose.py src/grounded_research/verify.py src/grounded_research/canonicalize.py src/grounded_research/anonymize.py src/grounded_research/analysts.py src/grounded_research/models.py tests/test_tyler_v1_stage1_runtime.py tests/test_verify.py tests/test_anonymize.py tests/test_tyler_v1_stage3_runtime.py tests/test_engine_fixture_loading.py tests/test_export.py tests/test_tyler_v1_stage5_6_adapters.py`
- `./.venv/bin/python -m pytest tests/test_tyler_v1_stage1_runtime.py tests/test_tyler_v1_stage4_adapters.py tests/test_engine_fixture_loading.py tests/test_phase_boundaries.py -q`
- `./.venv/bin/python -m pytest tests/test_verify.py tests/test_anonymize.py tests/test_phase_boundaries.py -q`
- `./.venv/bin/python -m pytest tests/test_tyler_v1_stage3_runtime.py tests/test_engine_fixture_loading.py tests/test_export.py tests/test_tyler_v1_stage5_6_adapters.py tests/test_phase_boundaries.py -q`
- `./.venv/bin/python -m pytest tests/test_verify.py tests/test_canonicalize.py tests/test_prompt_templates.py -q`

Outcome:

- `main` no longer defines or imports `QuestionDecomposition`, `AnalystRun`, or `ClaimLedger`
- the Stage 3 quality floor moved to canonical Tyler `AnalysisObject` validation
- remaining cutover debt is now narrower Stage 5 internal current-shape protocol debt

## Ordered Phases

### Phase 1: Tyler-native Stage 1 validation

- rewrite `validate_decomposition()` to validate `DecompositionResult`
  directly
- change `decompose_with_validation_tyler_v1()` to return only:
  - `DecompositionResult`
  - `DecompositionValidation | None`
- delete Stage 1 projection adapter helpers if no live callers remain:
  - `tyler_decomposition_to_current()`
  - `current_decomposition_to_tyler()`
- delete or rewrite Stage 1 adapter tests

Files:

- `src/grounded_research/decompose.py`
- `src/grounded_research/tyler_v1_adapters.py`
- `tests/test_tyler_v1_models.py`
- `tests/test_tyler_v1_stage1_runtime.py`
- `tests/test_tyler_v1_stage4_adapters.py`

### Phase 2: Delete legacy verification/build/anonymization helpers

- remove `verify_disputes()` from `verify.py`
- remove `build_ledger()` from `canonicalize.py`
- remove `scrub_analyst_run()` from `anonymize.py`
- delete or rewrite tests that only cover those current-shape helpers

Files:

- `src/grounded_research/verify.py`
- `src/grounded_research/canonicalize.py`
- `src/grounded_research/anonymize.py`
- `tests/test_verify.py`
- `tests/test_anonymize.py`

### Phase 3: Delete current-shape model classes

- remove `QuestionDecomposition` from `models.py`
- remove `AnalystRun` from `models.py`
- remove `ClaimLedger` from `models.py`
- rewrite any remaining tests/fixtures still constructing those classes

Files:

- `src/grounded_research/models.py`
- `tests/test_engine_fixture_loading.py`
- `tests/test_export.py`
- any remaining test files found by `rg`

### Phase 4: Rewrite authority docs and commit map

- update `docs/CONTRACTS.md`, `docs/PLAN.md`, `docs/ROADMAP.md`,
  `docs/ARCHITECTURE_ONE_PAGE.md`, `docs/DOMAIN_MODEL.md`,
  `docs/FEATURE_STATUS.md`, `docs/TYLER_LITERAL_PARITY_AUDIT.md`,
  `docs/TYLER_VARIANT_COMMIT_MAP.md`, and the plan index
- record the last commit that still contained the removed compatibility models

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| Stage 1 validation quietly depends on projected current fields | decomposition tests fail or prompt rendering breaks | render the validation prompt from Tyler fields directly; do not restore `QuestionDecomposition` |
| A deleted helper still supports a hidden live path | compile or phase-boundary tests fail | restore only the narrow internal behavior needed, then reopen a smaller child slice |
| Removing current-shape model classes breaks historical-only tests | test failures only in archived/compatibility fixtures | rewrite or delete those tests instead of restoring the model class |
| Active docs overstate deletion progress | active docs say current-shape models are fully gone while code still defines them | tighten the doc language immediately and keep the wave open until code and docs match |
