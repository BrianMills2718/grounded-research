# Tyler Frontier Runtime Validation Wave 1

`docs/TYLER_SPEC_GAP_LEDGER.md` is the canonical evidence source. This wave
exists to turn the remaining "frontier-model runtime validation" row into a
real pass/fail result instead of a standing assumption.

**Status:** Completed
**Type:** validation
**Priority:** High
**Blocked By:** live provider/model availability
**Blocks:** truthful closure of the remaining local Tyler-required runtime row

---

## Goal

Run one fully literal fixture-backed pipeline execution under the production
frontier config and prove, with run-local artifacts, whether the configured
frontier stack actually works as intended.

---

## Ledger Rows

- `STATUS-FRONTIER-RUNTIME-001`

---

## Scope

### In Scope

1. run `engine.py` against a saved fixture bundle that already has Tyler Stage 1
   and Stage 2 sidecars
2. use the production config, not `config.testing.yaml`
3. verify the run with:
   - final report/handoff artifacts
   - stage trace
   - run-local observability DB model usage
4. classify the outcome as:
   - `verified_fixed`
   - `open_shared_plan`
   - `open_local_followup`

### Out of Scope

- new prompt or orchestration patches
- additional retrieval collection work
- broad benchmark expansion
- shared Gemini schema-quality research

---

## Pre-Made Decisions

1. use a fixture-backed run, not a fresh web-collection run
   - reason: this isolates frontier-model execution from retrieval variance
2. use `output/full_run/collected_bundle.json` as the first validation slice
   because it already has `tyler_stage_1.json` and `tyler_stage_2.json`
3. require the run to complete with production-config models and produce a
   valid Tyler report/handoff
4. treat configured non-dominant synthesis-model selection as compliant
   behavior, not as an unwanted fallback
5. treat provider/runtime failure fallbacks during other stages as a failed
   validation for closure purposes
6. if the run fails for a shared provider/model reason, log it and continue by
   classifying the row accurately instead of pretending the row is closed

---

## Success Criteria

1. one production-config fixture run completes end to end
2. output directory contains:
   - `report.md`
   - `handoff.json`
   - `trace.json`
   - run-local `llm_observability.db`
3. observability evidence shows the live run used the intended frontier stage
   models, except where Stage 6 legitimately chooses a configured non-dominant
   synthesis alternative
4. the status docs and ledger are updated to reflect the actual result, not a
   hopeful interpretation

---

## Failure Modes

1. model unavailable or provider error
   - classify as shared/runtime blocked, preserve the artifacts, do not close
     the row
2. run completes only because an unexpected fallback model carried a stage
   - treat as failed validation for closure purposes
3. trace or observability artifacts are insufficient to prove model usage
   - leave the row open and open a trace-evidence follow-up instead of guessing

---

## Execution

1. run the fixture-backed production-config pipeline into a new output
   directory
2. inspect trace + observability DB for model usage by task
3. reconcile:
   - `docs/TYLER_EXECUTION_STATUS.md`
   - `docs/TYLER_SPEC_GAP_LEDGER.md`
   - `docs/plans/CLAUDE.md`
   - `docs/plans/tyler_faithful_execution_remainder.md`

---

## Verification Commands

- `./.venv/bin/python engine.py --fixture output/full_run/collected_bundle.json --output-dir output/tyler_frontier_runtime_validation_wave1`
- `sqlite3 output/tyler_frontier_runtime_validation_wave1/llm_observability.db '<query>'`

## Outcome

Completed on 2026-04-08.

Result:

1. the first literal production-config frontier run completed end to end
2. the intended primary models were actually used for Stage 3, Stage 4, Stage
   5, and Stage 6
3. the wave did **not** close the open row because the run exposed a real
   frontier-model reliability issue:
   - Gamma / Claude Opus failed the Stage 3 citation quality floor
   - the pipeline only completed because two successful analysts are sufficient

So this wave narrowed the remaining gap from "untested frontier config" to
"documented Claude Opus Stage 3 reliability failure under the literal run."

## Verification Results

- `./.venv/bin/python engine.py --fixture output/full_run/collected_bundle.json --output-dir output/tyler_frontier_runtime_validation_wave1`
- `python` stdlib `sqlite3` queries against `output/tyler_frontier_runtime_validation_wave1/llm_observability.db`
- artifact inspection:
  - `output/tyler_frontier_runtime_validation_wave1/trace.json`
  - `output/tyler_frontier_runtime_validation_wave1/summary.md`
