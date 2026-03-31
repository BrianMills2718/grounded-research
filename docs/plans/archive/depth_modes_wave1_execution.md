# Depth Modes Wave 1 Execution

**Status:** Completed
**Purpose:** Execute the next benchmark-driven depth continuation wave without
reopening broad cleanup work.

## Scope

This wave is intentionally narrower than the full long-term `depth_modes.md`
vision.

It covers only:

1. depth-aware goal-driven evidence extraction
2. depth-aware multi-round arbitration
3. benchmark verification and documentation updates

It does **not** promise sectioned synthesis in the same wave unless the
benchmark shows the current long-report path is the bottleneck.

## Why This Wave

`grounded-research` no longer has an open hardening backlog. The next
repo-local expansion should be the smallest benchmark-driven continuation of the
existing depth mode plan.

The most plausible remaining depth gap is:

- deeper evidence extraction from already-fetched pages
- deeper dispute follow-up when the first arbitration pass is inconclusive

These are repo-local product behaviors. They do not belong in shared
infrastructure.

## Pre-Made Decisions

1. Keep the current `depth` surface (`standard`, `deep`, `thorough`) unchanged.
2. Apply richer extraction only in `deep` and `thorough` mode. `standard`
   remains the cheap baseline.
3. Keep source count as the primary depth lever. Extraction depth is a
   secondary lever on already-selected pages.
4. Extraction output must reuse existing `EvidenceItem` contracts. No new
   public evidence schema is introduced in this wave.
5. Multi-round arbitration only applies when:
   - the depth profile allows more than one round, and
   - the prior round is `inconclusive`
6. Stop arbitration early if a round yields a non-inconclusive verdict.
7. If deeper extraction needs a page-text helper, add the smallest truthful
   helper in the existing fetch/read surface rather than inventing another
   opaque interface.
8. Sectioned synthesis remains deferred unless the benchmark proves the single
   long-report call is the active bottleneck.

## Files Affected

- `CLAUDE.md`
- `AGENTS.md`
- `docs/plans/CLAUDE.md`
- `docs/ROADMAP.md`
- `docs/plans/depth_modes_wave1_execution.md`
- `docs/notebooks/11_depth_modes_wave1.ipynb`
- `config/config.yaml`
- `src/grounded_research/config.py`
- `src/grounded_research/collect.py`
- `src/grounded_research/tools/fetch_page.py` (if a page-text helper is needed)
- `src/grounded_research/verify.py`
- `prompts/extract_evidence.yaml`
- tests covering collection, verification, and any new helper surface

## Steps

### Step 1: Goal-driven evidence extraction for deep/thorough

- add config for depth-aware evidence extraction enablement and target item
  counts
- add a prompt-backed extraction path that consumes page text plus the question
  and sub-question context
- keep `standard` mode on the current cheap notes/key-section path
- produce multiple `EvidenceItem`s per page in `deep` and `thorough` when the
  page contains distinct evidence-bearing material

Acceptance:
- `standard` mode behavior is unchanged
- `deep`/`thorough` collection can produce more than the current `notes` +
  `key_section` pair when the page supports it
- collection tests prove the depth switch and item creation behavior

### Step 2: Multi-round arbitration for deeper modes

- use the depth profile's `arbitration_max_rounds`
- if a dispute remains `inconclusive`, generate a new query batch and try
  another round up to the configured cap
- stop early when a round resolves the dispute
- keep warnings/trace state explicit across rounds

Acceptance:
- `standard` mode still uses one round
- `deep`/`thorough` can take a second/third round when prior rounds remain
  inconclusive
- verification tests prove round-capped looping and early exit on resolution

### Step 3: Benchmark and docs gate

- run at least one depth-mode benchmark gate after the code lands
- update roadmap/plan status to reflect the result
- record any residual uncertainty in `docs/TECH_DEBT.md` only if the benchmark
  exposes a new unresolved issue

Acceptance:
- targeted tests pass
- one benchmark or fixture gate is recorded
- plan/docs reflect the true result of this wave

## Required Tests

- `tests/test_collect.py`
- `tests/test_verify.py`
- `tests/test_phase_boundaries.py`
- new focused tests for any page-text helper or extraction helper added in this
  wave

## Result

Completed on `2026-03-26`.

Implemented:

1. depth-gated goal-driven evidence extraction for `deep` and `thorough`
2. truthful persisted-page helper via `read_page()`
3. explicit fallback to the legacy notes/key-section path with gap logging
4. depth-aware multi-round arbitration using `arbitration_max_rounds`

Verified:

- `PYTHONPATH=src python -m pytest tests/test_collect.py tests/test_verify.py tests/test_phase_boundaries.py -q`
  - `45 passed, 1 skipped`
- live deep-mode collection smoke:
  - output: `output/depth_wave1_smoke/`
  - question: `What do pilot programs and academic evidence suggest about universal basic income effects on labor supply?`
  - result: `5` sources, `19` evidence items, `14` LLM-extracted items, `0` gaps

Residual uncertainty:

- multi-round arbitration is verified by targeted tests in this wave, not by a
  saved live trace that required more than one arbitration round
- sectioned synthesis remains deferred until a benchmark shows the current
  single-call long-report path is the active bottleneck

## Failure Modes

| Failure mode | Detection | Response |
|---|---|---|
| deep extraction adds noisy duplicates instead of useful evidence | evidence count rises but canonicalization quality regresses | tighten extraction prompt and cap per-source evidence mechanically |
| deeper extraction regresses standard-mode cost/speed | standard tests or runtime behavior change | keep the richer path behind a depth gate |
| multi-round arbitration burns budget without changing outcomes | repeated inconclusive rounds with no new evidence delta | preserve the configured round cap and stop when no fresh evidence appears |
| sectioned synthesis becomes the real bottleneck instead | benchmark still loses on report depth despite richer evidence/arbitration | open a second depth continuation wave for sectioned synthesis |
