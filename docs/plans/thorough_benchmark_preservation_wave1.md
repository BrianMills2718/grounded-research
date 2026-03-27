# Thorough Benchmark Preservation Wave 1

**Status:** In Progress
**Purpose:** Remove the remaining repo-local uncertainty by running a fresh
`thorough` UBI fixture benchmark on the current code, comparing it to the
saved baseline, and only opening recent-first ranking if the completed run
points there.

## Scope

This wave covers only:

1. a fresh `thorough` fixture rerun on the best saved UBI bundle
2. fair comparison against cached Perplexity and the prior saved pipeline anchor
3. a decision on whether recent-first evidence ranking needs to become the next
   repo-local implementation wave

This wave does **not** cover:

- new retrieval providers
- new arbitration logic
- prompt-eval/provider studies
- non-benchmark-driven feature work

## Why This Wave

The repo-local hardening and depth waves are complete, but one real uncertainty
remains: the passing `thorough` sectioned-synthesis gate used a saved trace
rerender, not a fresh full benchmark run. The roadmap already says the next
repo-local move should be benchmark preservation or a new benchmark-triggered
wave.

## Pre-Made Decisions

1. Use the saved high-quality UBI fixture bundle at
   `output/ubi_wave2_prefetch_collection/collected_bundle.json`.
2. Use the paired decomposition file at
   `output/ubi_wave2_prefetch_collection/decomposition.json`.
3. Run via the fixture path, not a fresh cold-start collection run, because the
   current roadmap anchor is the runtime-safe fixture path.
4. Force `--depth thorough` for this wave.
5. Compare the new report against:
   - cached Perplexity
   - the prior saved pipeline anchor where useful
6. If the new run clearly preserves or improves the saved UBI result, close the
   wave with no further repo-local code changes.
7. If the new run regresses and the evidence clearly points to stale-source
   dominance, open recent-first ranking immediately as the next repo-local plan.
8. If the new run regresses but does **not** point to stale-source dominance,
   record the uncertainty and do not patch unrelated repo code in this wave.

## Files Expected

- `CLAUDE.md`
- `AGENTS.md`
- `docs/plans/CLAUDE.md`
- `docs/ROADMAP.md`
- `docs/plans/thorough_benchmark_preservation_wave1.md`
- `docs/notebooks/13_thorough_benchmark_preservation_wave1.ipynb`
- benchmark outputs under `output/`

## Steps

### Step 1: Run the fresh thorough fixture benchmark

- run `engine.py --fixture ... --decomposition ... --depth thorough`
- save the report and trace under a new output directory
- record key metrics:
  - claim count
  - dispute count
  - arbitration count
  - warning count
  - long-report word count

Acceptance:
- the run completes end-to-end
- the saved trace/report exist

### Step 2: Compare the fresh run

- run fair comparison against cached Perplexity
- compare against the prior saved pipeline anchor if useful for debugging
- inspect whether any regression is likely tied to stale-source dominance

Acceptance:
- a saved fair comparison exists
- the wave can make a clear repo-local/no-repo-local decision

### Step 3: Close the wave

- if benchmark preserved/improved: update docs and close
- if regression with stale-source dominance: open the next recent-first plan
- if regression without that diagnosis: record the uncertainty and close

Acceptance:
- roadmap/plan/index all match the actual outcome

## Required Tests

- existing benchmark scripts and trace/report artifacts are the main gate
- no new code means no new unit tests in the preserve/pass path

## Failure Modes

| Failure mode | Detection | Response |
|---|---|---|
| fixture rerun fails operationally | no saved report/trace | treat as runtime/shared-infra concern unless the failure is clearly repo-local |
| report regresses despite same bundle | fair comparison loses materially | inspect trace and source recency distribution before choosing a repo-local fix |
| stale-source dominance is not evident | old authoritative sources are not obviously crowding out newer relevant items | do not patch recent-first ranking speculatively |
| benchmark preserves the win | comparison still favors the pipeline | close the wave without adding repo-local complexity |
