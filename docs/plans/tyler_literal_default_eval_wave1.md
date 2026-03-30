# Tyler Literal Default Eval Wave 1

**Status:** Completed
**Type:** cross-repo evaluation
**Priority:** High
**Blocked By:** `prompt_eval` branch `plan-11-tyler-literal-eval` must remain
available in a clean worktree for execution
**Blocks:** default-policy decision for Tyler-literal versus archived
calibrated legacy behavior

## Goal

Run the first disciplined shared-eval comparison between the canonical
Tyler-literal runtime and the strongest archived calibrated legacy anchor
without reviving a second runtime path inside `grounded-research`.

This wave is complete when:

1. the frozen comparison case set is explicit and reproducible,
2. `prompt_eval` evaluates the saved outputs end to end,
3. the result is recorded in repo docs,
4. the default-policy decision and remaining uncertainties are explicit.

## Scope

In scope:

- frozen benchmark/output manifest for Tyler-literal vs calibrated legacy
- `grounded-research` script/harness that feeds saved artifacts into
  `prompt_eval`
- saved evaluation outputs under `output/`
- doc updates that record the decision and the next shared-infra follow-ups

Out of scope:

- reopening any deleted local compatibility runtime path
- changing the canonical Tyler runtime during this wave
- provider/runtime parity work in `llm_client` or `open_web_retrieval`

## Frozen Comparison Set

Wave 1 uses the strongest matched saved UBI artifacts already on disk:

- Tyler-literal recovered anchor:
  `output/tyler_literal_parity_ubi_reanchor_v8/`
- archived calibrated legacy anchor:
  `output/ubi_dense_dedup_eval/`

Why this set:

- it is the strongest matched Tyler-vs-legacy comparison currently available
  in one repo
- both artifacts include `report.md`, `summary.md`, `trace.json`, and
  `handoff.json`
- it avoids reintroducing an alternate runtime mode

Known limitation:

- this wave uses one shared question/case only
- statistical confidence is therefore weak; treat the result as a disciplined
  directional comparison, not as final ecosystem-wide proof

## Phases And Success Criteria

### Phase 1: Freeze The Comparison Manifest

Deliverables:

- a checked-in manifest that records:
  - case ID
  - question text
  - artifact directories
  - commit anchors
  - file hashes for the compared outputs

Success criteria:

- manifest loads without path ambiguity
- artifact paths exist
- file hashes are present for every compared file

Failure modes:

- missing artifact file
- ambiguous commit anchor
- compared outputs not actually matched to the same question

### Phase 2: Build The Shared-Eval Harness

Deliverables:

- a grounded-research script that:
  - reads the manifest,
  - constructs `prompt_eval.ExperimentInput` plus `PrecomputedOutput`,
  - evaluates the saved outputs with a quality rubric,
  - writes JSON and Markdown summaries under `output/`

Pre-made decisions:

- evaluate `report.md` as the primary comparison artifact
- use `prompt_eval.evaluate_precomputed_variants()`
- use a rubric derived from the existing fair-comparison dimensions:
  factual accuracy, completeness, conflict/nuance, analytical depth, decision
  usefulness
- use repeated judge scoring on the same frozen case to estimate judge noise
  rather than pretending one case yields strong statistical power

Success criteria:

- script runs from the repo root against the frozen manifest
- it emits a valid `EvalResult` JSON summary
- it emits a readable Markdown summary

Failure modes:

- import/setup drift between `grounded-research` and the clean `prompt_eval`
  worktree
- evaluator output not parseable into a normal `EvalResult`
- judge setup silently using an unreviewed prompt family

### Phase 3: Run The Frozen Comparison

Deliverables:

- saved eval outputs under `output/`
- a paired comparison summary between:
  - `tyler_literal`
  - `calibrated_legacy`

Success criteria:

- at least one full eval run completes without code errors
- the summary clearly reports:
  - mean score by variant
  - dimension means by variant
  - comparison result
  - observed uncertainty limits

Failure modes:

- LLM judge runtime failure
- observability/runtime contention
- result too ambiguous to support a default-policy decision

### Phase 4: Record The Decision And Next Follow-Through

Deliverables:

- updated docs that say:
  - whether Tyler-literal is the default
  - whether the archived calibrated anchor remains comparison-only
  - what shared-infra work is next

Success criteria:

- `ROADMAP.md`, `PLAN.md`, and `TYLER_VARIANT_COMMIT_MAP.md` all agree
- uncertainties are explicit, not implied

Failure modes:

- docs still imply two co-equal runtime modes
- result is recorded without its limits

## Executed Result

Wave 1 completed on 2026-03-29.

Frozen comparison outputs:

- manifest:
  `config/eval_manifests/tyler_literal_default_eval_wave1.json`
- harness:
  `scripts/eval_tyler_variants.py`
- saved eval outputs:
  `output/tyler_literal_default_eval_wave1/result.json`
  `output/tyler_literal_default_eval_wave1/summary.md`

Observed result with `openrouter/openai/gpt-5.4-mini` and `3` scoring
replicates per variant:

- `tyler_literal` mean score: `0.85`
- `calibrated_legacy` mean score: `0.6833`
- difference: `+0.1667`
- bootstrap CI: `[0.10, 0.25]`

Dimension means favored Tyler-literal on:

- factual accuracy
- completeness
- conflict and nuance
- decision usefulness

Analytical depth tied on this single-case eval.

## Todo List

- [x] Phase 1: freeze the comparison manifest
- [x] Phase 2: build the shared-eval harness
- [x] Phase 3: run the frozen comparison
- [x] Phase 4: record the decision and next follow-through

## Acceptance Rule

Wave 1 passes if:

- the comparison is frozen and reproducible,
- `prompt_eval` runs it end to end from saved artifacts,
- the result is recorded in canonical docs,
- the repo keeps one canonical Tyler runtime regardless of whether the archived
  calibrated anchor scores higher.

Important:

- this wave does **not** decide whether legacy should return as a runtime mode
- it decides only whether Tyler-literal remains the canonical target and what
  the next evidence-backed follow-up should be

## Decision

Tyler-literal remains the canonical default runtime target.

The archived calibrated legacy path remains:

- commit-reference history
- frozen benchmark artifact history
- eval-time comparison only

It does **not** return as a co-equal runtime mode in `main`.

## Remaining Uncertainty

This wave is based on one shared benchmark case only.

That means:

- the result is disciplined evidence, not ecosystem-wide proof
- expanding the frozen case set is still worthwhile
- any remaining model/provider/runtime gap should now be pursued in shared
  infrastructure rather than by reopening local compatibility code
