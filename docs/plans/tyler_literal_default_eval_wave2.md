# Tyler Literal Default Eval Wave 2

**Status:** Completed
**Type:** cross-repo evaluation
**Priority:** High
**Parent plan:** `docs/plans/tyler_faithful_execution_remainder.md`

## Goal

Expand the frozen Tyler-vs-legacy evidence beyond the single tracked UBI case
 without reviving any legacy runtime mode in `grounded-research`.

This wave uses one additional archived legacy benchmark with a saved fixture,
generates the corresponding current Tyler-literal report, scores the frozen
pair through `prompt_eval`, and records the two-case conclusion explicitly.

## Why This Needs Its Own Wave

The repo-local runtime and prompt literalness work are already complete. The
remaining evaluation gap is narrow:

- `tyler_literal_default_eval_wave1` proved the comparison path on one UBI case
- the remainder plan still cannot claim broad frozen evidence because that is
  still effectively one case

This wave closes that gap on the smallest real additional slice.

## Scope

In scope:

- one additional matched Tyler-vs-legacy frozen case
- saved artifacts in `grounded-research/output/`
- frozen-eval manifest(s) in `config/eval_manifests/`
- `scripts/eval_tyler_variants.py`
- docs summarizing the multi-case result

Out of scope:

- new runtime profiles
- prompt changes
- provider/model parity implementation
- broad benchmark expansion across many historical cases

## Pre-Made Decisions

1. Use the existing single-case frozen-eval harness rather than widening the
   manifest contract unless a second matched case truly requires it.
2. The additional case is PFAS because:
   - an archived calibrated legacy artifact already exists in
     `output/pfas_v2_analytical/`
   - a saved `collected_bundle.json` fixture exists there
   - the current Tyler-literal runtime can generate the comparison artifact
     without reopening legacy code
3. The current Tyler-literal side is generated from:
   - `output/pfas_v2_analytical/collected_bundle.json`
   - current `main`
   - one new output directory dedicated to this eval wave
4. The legacy side remains the archived reference in
   `output/pfas_v2_analytical/`.
5. Cross-case judgment is recorded as:
   - per-case frozen-eval summaries
   - one combined summary note in `grounded-research`
6. If the PFAS fixture run fails for a repo-local reason, fix it in this wave.
   If it fails for shared runtime/provider reasons, log the blocker explicitly
   and stop claiming the expanded frozen set is complete.

## Acceptance Criteria

This wave passes only if:

1. a new Tyler-literal PFAS artifact is generated from the saved PFAS bundle,
2. a frozen manifest for the PFAS pair is committed with verified hashes,
3. `scripts/eval_tyler_variants.py` runs successfully on that PFAS pair,
4. the repo records a two-case Tyler-vs-legacy conclusion with explicit limits,
5. docs/plans no longer describe the frozen evidence as effectively one case.

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| fixture mismatch | current Tyler output is not really answering the archived PFAS question | fail the wave; choose a different archived case rather than forcing a bad pair |
| shared-eval drift | `prompt_eval` path no longer runs from this repo environment | fix the environment dependency or record the exact external blocker |
| artifact instability | rerunning the PFAS fixture mutates the saved legacy side or reuses an ambiguous directory | use a new dedicated output dir and freeze hashes after generation |
| false breadth claim | docs say “broad evidence” from only two cases | record the result as two-case directional evidence, not broad proof |

## Phases

### Phase 1: Define The Second Frozen Pair

Deliverables:

- chosen archived case
- exact question text
- dedicated output dir for the current Tyler-literal counterpart
- wave notebook artifact

Pass if:

- the pair is clearly matched and reproducible

### Phase 2: Generate The Tyler-Literal PFAS Counterpart

Deliverables:

- one new output dir with:
  - `report.md`
  - `summary.md`
  - `trace.json`
  - `handoff.json`

Pass if:

- the run completes from the saved PFAS fixture and writes the canonical files

### Phase 3: Freeze And Score The PFAS Pair

Deliverables:

- PFAS frozen manifest
- saved PFAS eval result and summary

Pass if:

- manifest hashes verify
- frozen eval runs successfully

### Phase 4: Record The Two-Case Conclusion

Deliverables:

- combined summary note
- updated remainder plan / roadmap / plan index

Pass if:

- docs describe the frozen evidence as two-case directional evidence with
  explicit limits

## Verification

Minimum verification:

1. `python engine.py --fixture ... --output-dir ...` succeeds for the PFAS case
2. `./.venv/bin/python scripts/eval_tyler_variants.py --manifest ...`
   succeeds for the PFAS manifest
3. `./.venv/bin/python -m pytest tests/test_eval_tyler_variants.py -q`
4. manifest hash verification passes

## Todo List

- [x] Phase 1: define the second frozen pair
- [x] Phase 2: generate the Tyler-literal PFAS counterpart
- [x] Phase 3: freeze and score the PFAS pair
- [x] Phase 4: record the two-case conclusion

## 24h Execution Rule

This wave should continue until the PFAS pair is generated, scored, documented,
and committed, unless a real shared-infra/runtime blocker appears. Do not stop
after selecting the case or after generating the report; the wave closes only
after the frozen comparison and the docs are updated.
