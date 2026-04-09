# Tyler Exact Model Version Switch Wave 1

**Status:** Completed
**Type:** implementation
**Priority:** High
**Parent plan:** `docs/plans/tyler_shared_model_version_parity_wave1.md`

## Goal

Switch the live `grounded-research` production config from
`openrouter/google/gemini-2.5-pro` to
`openrouter/google/gemini-3.1-pro-preview` on the Tyler-named Gemini roles,
then run one real validation that exercises those roles through the live app.

## Scope

In scope:

- `config/config.yaml` production Gemini role surfaces
- exact-model status/ledger docs
- one raw-question validation run that exercises:
  - Stage 1 decomposition
  - Stage 2 evidence extraction/source scoring
  - Stage 3 structured-decomposition analyst

Out of scope:

- testing config changes
- broader benchmark expansion
- prompt rewrites
- model-policy changes for non-Tyler roles

## Pre-Made Decisions

1. Only the Tyler-named Gemini 3.1 Pro roles switch:
   - `models.decomposition`
   - `models.evidence_extraction`
   - `models.source_scoring`
   - `analyst_models[1]` / Analyst B
2. `models.query_diversification` stays on the cheaper lightweight path unless
   Tyler explicitly required Gemini 3.1 Pro there.
3. Validation is a raw-question run, not a fixture-backed run, because the goal
   is to exercise the Stage 1/2 Gemini surfaces as well as Stage 3.
4. Use one moderate real question instead of reopening broad benchmark work:
   - `What are Palantir Technologies' major U.S. government contracts?`
5. The row closes only if:
   - config is switched,
   - the live run completes,
   - and observability proves the intended Gemini 3.1 Pro preview surface was
     actually used on the Tyler Gemini stages.

## Success Criteria

This wave passes only if:

1. production config now names `openrouter/google/gemini-3.1-pro-preview` on
   the Tyler Gemini roles,
2. Stage 3 config tests still pass,
3. the raw-question validation run completes with final artifacts,
4. run-local observability shows the intended Gemini 3.1 Pro preview surface on
   the switched stages,
5. the ledger/status docs are updated truthfully.

## Verification

Minimum verification:

1. `tests/test_tyler_v1_stage3_runtime.py`
2. raw run:
   - `./.venv/bin/python engine.py "What are Palantir Technologies' major U.S. government contracts?" --output-dir output/tyler_exact_model_version_switch_wave1_palantir`
3. inspect the run-local `llm_observability.db` for Gemini 3.1 Pro preview
4. reconcile:
   - `docs/TYLER_SPEC_GAP_LEDGER.md`
   - `docs/TYLER_EXECUTION_STATUS.md`
   - `docs/TYLER_SHARED_INFRA_OWNERSHIP.md`

## Todo List

- [x] switch production config
- [x] update config-sensitive tests
- [x] run raw-question validation
- [x] inspect observability/model usage
- [x] update ledger and status docs

## Completion Note

This wave closed on 2026-04-09.

Production config now uses `openrouter/google/gemini-3.1-pro-preview` for:

- `models.decomposition`
- `models.evidence_extraction`
- `models.source_scoring`
- `analyst_models[1]` / Analyst B

Verification passed:

1. `tests/test_tyler_v1_stage3_runtime.py`
2. raw-question run:
   - `./.venv/bin/python engine.py "What are Palantir Technologies' major U.S. government contracts?" --output-dir output/tyler_exact_model_version_switch_wave1_palantir`
3. run-local observability DB showed:
   - `question_decomposition_tyler_v1` → `openrouter/google/gemini-3.1-pro-preview` (`1`)
   - `finding_extraction_tyler_v1` → `openrouter/google/gemini-3.1-pro-preview` (`52`)
   - Analyst B `analyst_reasoning_tyler_v1` → `openrouter/google/gemini-3.1-pro-preview` (`1`)
   - `query_diversification_tyler_v1` intentionally remained on
     `openrouter/google/gemini-2.5-pro` (`4`)
4. final artifacts were written successfully:
   - `report.md`
   - `summary.md`
   - `trace.json`
   - `handoff.json`
