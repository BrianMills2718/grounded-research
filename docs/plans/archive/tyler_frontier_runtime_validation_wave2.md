# Tyler Frontier Runtime Validation Wave 2

`docs/TYLER_SPEC_GAP_LEDGER.md` is the canonical evidence source. Wave 1 proved
that the production frontier stack is callable on a literal run, but it left
the row open because the Claude Opus Stage 3 analyst failed the citation
quality floor once. This wave determines whether that failure is reproducible.

**Status:** Completed
**Type:** validation
**Priority:** High
**Blocked By:** live provider/model availability
**Blocks:** narrowing `STATUS-FRONTIER-RUNTIME-001` from "one failed literal run"
to either a reproducible frontier reliability defect or a narrower intermittent
issue

---

## Goal

Establish whether the Stage 3 Claude Opus citation-floor failure is:

1. reproducible on the same fixture,
2. reproducible on a second saved fixture,
3. or isolated/intermittent.

---

## Ledger Rows

- `STATUS-FRONTIER-RUNTIME-001`

---

## Scope

### In Scope

1. rerun the production frontier config on `output/full_run/collected_bundle.json`
2. run the production frontier config on one second saved fixture with Tyler
   Stage 1/2 sidecars
3. compare:
   - analyst success/failure
   - actual model usage
   - whether Claude Opus violates the Stage 3 source-citation quality floor
4. update the ledger/status docs with a more precise classification

### Out of Scope

- model substitution
- prompt rewrites
- schema changes
- shared Gemini study

---

## Pre-Made Decisions

1. use fixture-backed runs only
2. rerun `output/full_run/collected_bundle.json` first to test repeatability
3. use `output/what_are_palantir_technologies'_major_us/collected_bundle.json`
   as the second saved fixture because it already has Tyler Stage 1/2 sidecars
4. treat repeated Claude Opus Stage 3 citation-floor failure as evidence of a
   real frontier reliability defect, not noise
5. if one run passes and one fails, classify the row as intermittent rather
   than closed

---

## Success Criteria

1. two additional production-config fixture runs complete
2. each run has:
   - `trace.json`
   - `summary.md`
   - `llm_observability.db`
3. the docs can classify the remaining row as one of:
   - reproducible frontier reliability defect
   - intermittent frontier reliability defect
   - cleared on repeat

---

## Verification Commands

- `./.venv/bin/python engine.py --fixture output/full_run/collected_bundle.json --output-dir output/tyler_frontier_runtime_validation_wave2_repeat`
- `./.venv/bin/python engine.py --fixture "output/what_are_palantir_technologies'_major_us/collected_bundle.json" --output-dir output/tyler_frontier_runtime_validation_wave2_palantir`

## Outcome

Completed on 2026-04-08.

Results:

1. the repeat run on `output/full_run/collected_bundle.json` passed cleanly
2. the second saved Palantir fixture also passed cleanly
3. both additional runs used the same intended primary models as Wave 1

This means the Wave 1 Claude Opus Stage 3 citation-floor failure is **not**
straightforwardly reproducible. The open row narrows to an intermittent
frontier reliability issue.

## Verification Results

- `./.venv/bin/python engine.py --fixture output/full_run/collected_bundle.json --output-dir output/tyler_frontier_runtime_validation_wave2_repeat`
- `./.venv/bin/python engine.py --fixture "output/what_are_palantir_technologies'_major_us/collected_bundle.json" --output-dir output/tyler_frontier_runtime_validation_wave2_palantir`
- `python` stdlib `sqlite3` queries against both run-local `llm_observability.db`
- artifact inspection:
  - `output/tyler_frontier_runtime_validation_wave2_repeat/trace.json`
  - `output/tyler_frontier_runtime_validation_wave2_palantir/trace.json`
