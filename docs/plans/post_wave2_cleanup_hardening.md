# Plan: Post-Wave-2 Cleanup And Hardening

**Status:** Active
**Type:** implementation
**Priority:** High
**Blocked By:** None
**Blocks:** Clean post-v0.1 documentation and the next benchmark wave

---

## Trigger

Wave 2 recovered the tracked UBI benchmark and cleared the runtime blocker.
The remaining work is now narrower and mostly internal:

- dense canonicalization on enumeration-heavy bundles is still weaker than ideal
- some prompt/config/schema issues remain in `docs/TECH_DEBT.md`
- sub-question evidence tagging is still query-origin based rather than
  relevance based
- phase-trace construction is correct at write time but still uses a fragile
  post-append mutation pattern

These issues are no longer top-level benchmark blockers, but they are the main
remaining internal cleanup before the next serious evaluation wave.

---

## Goal

Finish the remaining repo-local hardening work without reopening settled design
questions or changing the cheap-model development baseline.

Specifically:

1. improve dense canonicalization on enumeration-heavy questions
2. remove remaining prompt/config hygiene debt
3. harden fragile schema/trace construction details
4. improve sub-question evidence tagging so coverage checks reflect actual
   relevance instead of only search-query origin

Out of scope:

- production-model swaps
- new search providers as a first move
- shared-infra fixes that belong in `llm_client` or `open_web_retrieval`

---

## Files Likely Affected

- `src/grounded_research/canonicalize.py`
- `prompts/dedup.yaml`
- `src/grounded_research/collect.py`
- `src/grounded_research/source_quality.py`
- `prompts/query_generation.yaml`
- `prompts/source_scoring.yaml`
- `prompts/synthesis.yaml`
- `prompts/long_report.yaml`
- `src/grounded_research/models.py`
- `engine.py`
- `config/config.yaml`
- `tests/test_canonicalize.py`
- `tests/test_collect.py`
- `tests/test_export.py`
- `tests/test_phase_boundaries.py`
- `docs/TECH_DEBT.md`

---

## Pre-Made Decisions

1. Dense canonicalization stays LLM-first, but the control logic remains
   code-owned.
2. Enumeration-heavy canonicalization should stay conservative: distinct
   programs/studies do not merge unless the evidence context and claim content
   are genuinely equivalent.
3. Remaining inline prompts move to YAML/Jinja2 templates instead of staying as
   Python strings.
4. Hardcoded truncation limits move to config rather than new prompt-local
   constants.
5. Sub-question evidence tagging is improved inside this repo before any new
   provider/search diversification work.
6. Shared-infra issues already mitigated locally stay documented here, but
   their real fixes belong in shared libraries and do not block this plan.

---

## Workstreams

### 1. Dense Canonicalization Hardening

- inspect the current bucketed dedup behavior on enumeration-heavy runs
- add stronger non-merge criteria where the current staging still leaves
  `raw == canonical`
- make the raw-to-canonical mapping easier to inspect in tests and trace review

Pass condition:
- enumeration-heavy benchmark traces no longer default to effectively
  no-op canonicalization when genuine overlaps exist

### 2. Prompt And Config Hygiene

- move query-generation prompt into `prompts/query_generation.yaml`
- move source-quality scoring prompt into `prompts/source_scoring.yaml`
- move hardcoded synthesis truncation and evidence caps into `config/config.yaml`

Pass condition:
- no remaining known inline prompt debt on active call sites
- truncation/evidence-cap policy is config-driven rather than template-literal

Status:
- completed on 2026-03-26
- query generation and source scoring now render from YAML prompt files
- synthesis evidence caps and truncation limits now come from
  `config/config.yaml`

### 3. Schema And Trace Construction Hardening

- replace the `counterarguments` default/min-length fragility with an explicit
  validator policy
- stop mutating `PhaseTrace` after append; construct it once with final values

Pass condition:
- schema behavior no longer depends on Pydantic default-factory quirks
- phase traces are constructed atomically

Status:
- completed on 2026-03-26
- `AnalystRun.counterarguments` now validates explicitly only for successful
  runs
- export `PhaseTrace` is now constructed atomically after both synthesis calls

### 4. Sub-Question Evidence Tagging

- stop treating first-query origin as the full semantic tag
- add a better relevance-based tagging pass or explicit multi-tag strategy

Pass condition:
- coverage checks no longer show obvious false-zero sub-question coverage when
  the bundle clearly contains relevant evidence

---

## Failure Modes

| Failure Mode | Detection | Response |
|--------------|-----------|----------|
| Dense canonicalization improves merge rate by collapsing distinct programs | canonical count drops sharply and named-program distinctions disappear | strengthen non-merge rules before accepting the change |
| Prompt migration changes behavior unexpectedly | benchmark or prompt-template tests regress after YAML migration | land prompt moves in small slices and verify the rendered prompt text |
| Configuring truncation creates hidden prompt drift | report structure changes materially after moving limits into config | freeze defaults first, then externalize without changing values |
| Better evidence tagging adds noise instead of relevance | more sub-questions appear covered but report precision falls | tighten the tagging contract and inspect false-positive examples |

---

## Acceptance Criteria

- [ ] Dense enumeration-heavy runs improve beyond effectively `raw == canonical`
      no-op behavior when genuine overlaps exist
- [x] Remaining active inline prompt debt is moved into YAML prompt files
- [x] Synthesis truncation/evidence-cap limits are configurable in
      `config/config.yaml`
- [x] `AnalystRun.counterarguments` no longer relies on fragile default/min-length
      interaction
- [x] `PhaseTrace` is constructed atomically rather than post-mutated
- [ ] Sub-question evidence tagging no longer obviously undercounts relevant
      evidence on known benchmark cases
- [ ] Tests covering canonicalization, collection, export, and phase boundaries
      pass after each slice

---

## Verification

Minimum verification surface for this plan:

- `PYTHONPATH=src python -m pytest tests/test_canonicalize.py`
- `PYTHONPATH=src python -m pytest tests/test_collect.py`
- `PYTHONPATH=src python -m pytest tests/test_export.py`
- `PYTHONPATH=src python -m pytest tests/test_phase_boundaries.py`

Add benchmark reruns only after the dense-canonicalization slice is verified in
unit and phase-boundary tests.

Current verified slice:

- `PYTHONPATH=src python -m pytest tests/test_prompt_templates.py tests/test_export.py tests/test_collect.py tests/test_phase_boundaries.py -q`
  - Result: `48 passed, 1 skipped`
