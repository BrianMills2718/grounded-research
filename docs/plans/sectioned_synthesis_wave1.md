# Sectioned Synthesis Wave 1

**Status:** In Progress
**Purpose:** Prove whether the current single-call long-report path is the
active depth bottleneck, and implement sectioned synthesis only if the gate
shows that `thorough` mode undershoots its target.

## Scope

This wave covers only:

1. a thorough-mode export gate on a real saved calibrated trace
2. sectioned long-report synthesis if the gate fails
3. verification and documentation closure

This wave does **not** cover:

- new retrieval work
- new arbitration logic
- prompt-eval/provider comparisons
- broader report-style redesign beyond what sectioned synthesis requires

## Why This Wave

Wave 1 depth continuation already shipped richer evidence extraction and
multi-round arbitration. The remaining candidate in `depth_modes.md` is
sectioned synthesis, but the roadmap explicitly says not to open that work
without a benchmark-triggered reason.

The saved calibrated report shows the current single-call path is functional,
but a real `thorough`-mode rerender still needs to prove whether it can reach
the configured `10,000-15,000` word target with stable structure.

## Pre-Made Decisions

1. Use a saved high-quality trace as the gate input instead of paying for a
   full new end-to-end benchmark before touching export.
2. The gate trace is `output/ubi_wave2_report_calibrated/trace.json`.
3. Force `depth = thorough` only for the export gate. Do not reopen earlier
   pipeline phases in this wave.
4. If the single-call long report renders fewer than `9,000` words, treat that
   as a failed gate for `thorough` mode and implement sectioned synthesis.
5. Sectioned synthesis should reuse the existing long-report prompt rather than
   invent a second report style.
6. Sectioned synthesis should render:
   - core framing
   - one section per key distinction
   - broader implications / uncertainty / verdict / alternatives
   then join them into one markdown report.
7. Keep the current single-call path available for `standard` mode. Use the
   sectioned path only for deeper modes or when the word target exceeds a
   configured threshold.
8. If the gate meets the target with stable structure, do **not** implement
   sectioned synthesis in this wave. Close the plan with the benchmark result.

## Files Expected

- `CLAUDE.md`
- `AGENTS.md`
- `docs/plans/CLAUDE.md`
- `docs/ROADMAP.md`
- `docs/plans/sectioned_synthesis_wave1.md`
- `docs/notebooks/12_sectioned_synthesis_wave1.ipynb`
- `src/grounded_research/export.py`
- `config/config.yaml` if sectioned controls are required
- `tests/test_export.py`

## Steps

### Step 1: Run the thorough export gate

- load the saved calibrated trace into `PipelineState`
- force `depth = thorough`
- rerender the long report on the saved state
- record:
  - word count
  - heading count
  - placeholder/repair behavior
  - whether the output plausibly reaches the target depth

Acceptance:
- the gate is saved under `output/`
- the result is recorded in this plan
- the gate makes the sectioned-synthesis decision unambiguous

### Step 2: Implement sectioned synthesis only if the gate fails

- split the long report into a small number of substantive section renders
- keep citations, structure, and repair behavior explicit
- join the sections into one markdown artifact
- use config/runtime policy instead of hardcoded thresholds

Acceptance:
- `standard` mode behavior stays available
- deeper modes can render a longer report through section composition
- export tests cover the new path

### Step 3: Verification and docs closure

- rerun targeted export tests
- rerun the thorough export gate
- update roadmap/plan/index to reflect the actual result

Acceptance:
- tests pass
- one saved rerender gate exists
- docs reflect whether sectioned synthesis is now shipped or still deferred

## Required Tests

- `tests/test_export.py`
- any focused tests added for section planning/joining logic

## Failure Modes

| Failure mode | Detection | Response |
|---|---|---|
| single-call thorough rerender already hits target | gate output >= 9,000 words with stable structure | close the plan without more code |
| sectioned synthesis inflates length but loses coherence | output longer but structurally worse | tighten section contracts and keep a joining pass |
| sectioned synthesis breaks grounding/style continuity | tests or rerender show citation drift or placeholder regressions | preserve repair logic and keep the same prompt family across sections |
| output length improves but benchmark utility does not | later benchmark still underwhelms | record the uncertainty and open the next wave from the benchmark, not from style preference |
