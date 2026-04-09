# Tyler Literal Default Eval Wave 3: LLM SWE

**Status:** Planned
**Type:** cross-repo evaluation
**Priority:** High
**Parent plan:** `docs/plans/tyler_faithful_execution_remainder.md`

## Goal

Expand the frozen Tyler-vs-legacy evidence beyond the current two-case set by
adding one non-policy/non-public-health technical case.

This wave uses the saved `llm_swe_v3` technical anchor, generates the current
Tyler-literal counterpart from the archived collected bundle, scores the pair
through the existing frozen-eval harness, and records the three-case status
truthfully.

## Why This Wave

The current frozen evidence is directionally useful but still narrow:

- UBI and PFAS are both evidence-heavy policy/public-health cases
- `docs/TYLER_FROZEN_EVAL_STATUS.md` explicitly says the next case should be
  outside that cluster

This wave closes that exact breadth gap on the smallest real technical slice
already saved on disk.

## Scope

In scope:

- one additional matched technical Tyler-vs-legacy frozen case
- saved artifacts already in `output/llm_swe_v3/`
- one new Tyler-literal output directory
- one new frozen manifest
- the existing `scripts/eval_tyler_variants.py` harness
- status docs summarizing the three-case result

Out of scope:

- new runtime modes
- prompt or model changes
- new judge methodology
- broad archive backfill across many historical cases

## Pre-Made Decisions

1. Use `output/llm_swe_v3/` as the archived calibrated legacy anchor because:
   - it is a technical/non-public-health case
   - it already includes `collected_bundle.json`
   - it already includes the canonical frozen files
2. Generate the Tyler-literal side from:
   - `output/llm_swe_v3/collected_bundle.json`
   - current `main`
   - dedicated output dir `output/tyler_literal_llm_swe_eval_wave3/`
3. Save the eval result in:
   - `output/tyler_literal_default_eval_wave3_llm_swe/`
4. Keep the legacy side eval-only; do not reopen any legacy runtime path.
5. If the fixture run fails for a repo-local reason, fix it in this wave.
   If it fails for a shared runtime/provider reason, record that blocker
   explicitly and do not pretend the three-case set is complete.

## Acceptance Criteria

This wave passes only if:

1. a new Tyler-literal `llm_swe` artifact is generated from the saved fixture,
2. a frozen manifest for the `llm_swe` pair is committed with verified hashes,
3. `scripts/eval_tyler_variants.py` runs successfully on that manifest,
4. the repo records a three-case Tyler-vs-legacy conclusion with explicit
   limits,
5. docs no longer describe the frozen evidence as only a two-case story.

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| fixture mismatch | the new Tyler output is not answering the same `llm_swe` question as the archived artifact | fail the wave; choose a different technical anchor instead of forcing a bad pair |
| shared-eval drift | `prompt_eval` frozen-eval path no longer runs from the repo environment | fix the environment dependency or record the exact external blocker |
| artifact instability | rerun mutates the legacy side or reuses an ambiguous output dir | use a new dedicated Tyler output dir and freeze hashes only after generation |
| false breadth claim | docs start implying broad ecosystem proof from only three cases | record the result as three-case directional evidence, not broad proof |

## Phases

### Phase 1: Define The Technical Frozen Pair

Deliverables:

- chosen archived technical case
- exact question text
- dedicated Tyler-literal output dir
- wave notebook artifact

Pass if:

- the pair is clearly matched and reproducible

### Phase 2: Generate The Tyler-Literal LLM SWE Counterpart

Deliverables:

- `output/tyler_literal_llm_swe_eval_wave3/` with:
  - `report.md`
  - `summary.md`
  - `trace.json`
  - `handoff.json`

Pass if:

- the run completes from the saved `llm_swe_v3` fixture

### Phase 3: Freeze And Score The Pair

Deliverables:

- `config/eval_manifests/tyler_literal_default_eval_wave3_llm_swe.json`
- `output/tyler_literal_default_eval_wave3_llm_swe/result.json`
- `output/tyler_literal_default_eval_wave3_llm_swe/summary.md`

Pass if:

- manifest hashes verify
- frozen eval runs successfully

### Phase 4: Record The Three-Case Conclusion

Deliverables:

- updated `docs/TYLER_FROZEN_EVAL_STATUS.md`
- updated `docs/TYLER_EXECUTION_STATUS.md`
- updated roadmap/plan surfaces

Pass if:

- docs describe the frozen evidence as a three-case directional result with
  explicit limits

## Verification

Minimum verification:

1. `python engine.py --fixture output/llm_swe_v3/collected_bundle.json --output-dir output/tyler_literal_llm_swe_eval_wave3` succeeds
2. `./.venv/bin/python scripts/eval_tyler_variants.py --manifest config/eval_manifests/tyler_literal_default_eval_wave3_llm_swe.json --output-dir output/tyler_literal_default_eval_wave3_llm_swe --repeats 3` succeeds
3. `./.venv/bin/python -m pytest tests/test_eval_tyler_variants.py -q`
4. manifest hash verification passes

## Todo List

- [ ] Phase 1: define the technical frozen pair
- [ ] Phase 2: generate the Tyler-literal counterpart
- [ ] Phase 3: freeze and score the pair
- [ ] Phase 4: record the three-case conclusion

## 24h Execution Rule

This wave should continue until the `llm_swe` pair is generated, scored,
documented, and committed, unless a real shared-infra/runtime blocker appears.
Do not stop after selecting the case or after generating the report; the wave
closes only after the frozen comparison and the docs are updated.
