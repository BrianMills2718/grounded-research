# Tyler Remediation Phase 5: Stage 1/2 Retrieval And Scoring

`docs/TYLER_SPEC_GAP_LEDGER.md` is the canonical evidence source. This child
wave executes the remaining verified local Stage 1 and Stage 2 Tyler gaps.

**Status:** Completed
**Type:** implementation
**Priority:** Critical
**Blocked By:** `docs/TYLER_SPEC_GAP_LEDGER.md`
**Blocks:** truthful local Tyler closure claims for Stage 1 and Stage 2

---

## Goal

Bring the live Stage 1 and Stage 2 runtime into line with Tyler's requested
behavior without pulling shared-infra-blocked controls back into
`grounded-research`.

This wave exists because the current local divergences are now narrow and
verified:

1. Stage 1 still runs the removed validation/retry layer.
2. Stage 2 query diversification is deterministic code instead of the Tyler
   lightweight-model prompt.
3. Stage 2 routes every query through Tavily + Exa instead of routing by query
   role.
4. Stage 2 final `quality_score` still collapses to quality-tier mapping
   instead of Tyler's authority + freshness + staleness pipeline.

---

## Ledger Rows

- `S1-VALIDATION-001`
- `S2-QUERY-MODEL-001`
- `S2-ROUTING-001`
- `S2-QUALITY-001`
- `DOC-S2-QUERY-001`
- `DOC-S2-QUERY-002`

---

## Scope

### In Scope

1. Delete the live Stage 1 validation/retry path.
2. Add the missing Stage 2 query-diversification prompt and call it in the live
   runtime.
3. Introduce an explicit local Stage 2 query-plan contract so routing is typed
   and testable.
4. Route Stage 2 queries by query role using only shared retrieval controls
   that already exist.
5. Replace coarse tier-only Stage 2 final scoring with a deterministic blended
   score pipeline.
6. Fix the paired docs/status overclaims that still describe the old Stage 1/2
   behavior.

### Out of Scope

- shared Tavily controls beyond the current `SearchQuery` contract
- Exa `systemPrompt` support in shared infra
- shared-infra-only rows:
  - `S2-TAVILY-DEPTH-001`
  - `S2-EXA-CONTROLS-001`
- broader retrieval redesign outside Tyler's verified Stage 2 clauses

---

## Pre-Made Decisions

1. **Stage 1 delete-first:** the live runtime will call
   `decompose_question_tyler_v1()` directly. The validation prompt, validation
   model, and retry wrapper are deleted unless a non-live test/helper surface
   proves they still have a current caller.

2. **No fake "close enough" Stage 2 prompt literalness:** add
   `prompts/tyler_v1_query_diversification.yaml` and call it with a dedicated
   lightweight model config key.

3. **Dedicated config key:** add `models.query_diversification` plus matching
   fallback chain. Do not hide query diversification under `analyst` or
   `evidence_extraction`.

4. **Typed local query plan:** the runtime will not pass around raw strings for
   Tyler Stage 2 routing. Introduce a small local typed query-plan surface that
   carries:
   - `provider`
   - `query_role`
   - `query_text`
   - `sub_question_id`
   - `search_depth`
   - `result_detail`
   - `detail_budget`
   - `corpus`

5. **Routing rule for this local wave:**
   - KEYWORD / PRACTITIONER / CONTRARIAN → Tavily
   - SEMANTIC_DESCRIPTION → Exa
   - High-priority sub-questions keep the Exa semantic variant
   - Non-high-priority sub-questions may drop the Exa semantic variant
   - Time-sensitive Stage 2 Tavily queries use `corpus="news"` when that
     matches the Stage 2 routing table; otherwise keep `general`

6. **Use only currently available shared controls:**
   - Tavily: `search_depth`, `result_detail`, `detail_budget`, `corpus`,
     domain include/exclude, recency days
   - Exa: `search_depth`, `result_detail`, `detail_budget`, `corpus`
   - Do not emulate unsupported Exa `systemPrompt` locally

7. **Stage 2 local depth/detail defaults for this wave:**
   - Tavily keyword/practitioner/contrarian queries use
     `search_depth="basic"` and `result_detail="summary"`
   - Exa semantic queries use `search_depth="advanced"` and
     `result_detail="chunks"`
   - `detail_budget=3` on Exa semantic queries

8. **Stage 2 final scoring is deterministic and local:**
   - authority lookup from domain/source type
   - optional freshness blend from publication date
   - authority floor for seminal/official patterns
   - staleness modifiers from the first 2000 characters of fetched content
   - final score stored explicitly on the local `SourceRecord`

9. **Config-first policy values:** half-life days, temporal weights,
   staleness penalties, and authority floor behavior go in config, not hidden
   constants.

10. **Docs cleanup is part of the same wave:** do not leave known Stage 2
    overclaims in status docs after the runtime changes land.

---

## Implementation Surfaces

### Runtime

- `src/grounded_research/decompose.py`
- `engine.py`
- `src/grounded_research/collect.py`
- `src/grounded_research/source_quality.py`
- `src/grounded_research/tools/web_search.py`
- `src/grounded_research/models.py`
- `config/config.yaml`
- `config/config.testing.yaml`
- `prompts/tyler_v1_query_diversification.yaml`

### Tests

- `tests/test_tyler_v1_stage1_runtime.py`
- `tests/test_tyler_v1_stage2_runtime.py`
- `tests/test_collect.py`
- `tests/test_source_quality.py`
- `tests/test_web_search.py`
- any affected engine or phase-boundary tests

### Docs

- `docs/TYLER_SPEC_GAP_LEDGER.md`
- `docs/TYLER_EXECUTION_STATUS.md`
- `docs/plans/tyler_gap_remediation_wave1.md`
- `docs/plans/CLAUDE.md`
- `docs/PLAN.md`
- `docs/TYLER_LITERAL_PARITY_AUDIT.md`
- `docs/TYLER_LITERAL_PROMPT_FIDELITY_AUDIT.md`
- `docs/TYLER_PROMPT_LITERALNESS_MATRIX.md`
- `docs/FEATURE_STATUS.md`

---

## Acceptance Criteria

This wave passes only if all of the following are true:

1. No live Stage 1 validation/retry path remains.
2. The question-entry pipeline no longer prints or persists Stage 1 validation
   output.
3. Stage 2 query diversification is a lightweight model call backed by a real
   Tyler prompt file.
4. The Stage 2 runtime executes typed query plans, not raw string-only routing.
5. Stage 2 no longer sends every query to both Tavily and Exa.
6. Final Stage 2 `quality_score` is no longer produced by a direct tier map.
7. Tests prove:
   - Stage 1 no-validation behavior
   - Stage 2 query-plan shape
   - Stage 2 provider routing by query role
   - Stage 2 final scoring uses freshness/staleness adjustments
8. The ledger rows above move to `verified_fixed`.
9. Status/parity docs stop claiming the old deterministic-string-template
   behavior is literal Tyler.

---

## Verification

Minimum required verification:

1. Targeted unit tests:
   - Stage 1 entrypoint
   - Stage 2 query diversification
   - Stage 2 routing
   - Stage 2 scoring

2. Boundary tests:
   - at least one collection-path test through `collect_evidence()`
   - at least one question-entry pipeline test through `run_pipeline_from_question()`

3. Static checks:
   - `py_compile` on touched runtime files

4. Truth surfaces:
   - ledger row status updates
   - status doc reconciliation

---

## Failure Modes

1. Replacing the query generator but leaving `_search_one()` dual-provider
   behavior intact.
2. Deleting validation helpers but leaving `engine.py` or docs on the removed
   tuple return contract.
3. Adding an Exa-local hack for missing shared controls instead of logging the
   remaining shared-infra boundary.
4. Replacing the numeric tier map while still never using publication date or
   fetched content.
5. Fixing the code but leaving stale literalness/status claims in docs.

---

## Exit Condition

This plan is complete when:

1. Stage 1 validation is removed from the live path.
2. Stage 2 query generation, routing, and scoring are patched and verified.
3. The listed ledger rows are updated.
4. The remaining Stage 2 shared-infra gaps are still explicit and still
   outside `grounded-research`.

---

## Outcome

Completed on 2026-04-08.

Landed behavior:

1. deleted the live Stage 1 validation/retry path and removed
   `prompts/validate_decomposition.yaml`
2. cut question-entry execution over to `decompose_question_tyler_v1()`
3. added `prompts/tyler_v1_query_diversification.yaml` plus dedicated
   `models.query_diversification` config
4. replaced deterministic Stage 2 string templates with a lightweight
   structured query-diversification call that emits typed `Stage2QueryPlan`
   objects
5. routed Stage 2 queries by query role/provider instead of dual-provider
   fan-out
6. replaced tier-only final scoring with deterministic authority/freshness/
   staleness scoring and persisted the result on `SourceRecord.quality_score`
7. updated ledger rows `S1-VALIDATION-001`, `S2-QUERY-MODEL-001`,
   `S2-ROUTING-001`, `S2-QUALITY-001`, `DOC-S2-QUERY-001`, and
   `DOC-S2-QUERY-002` to `verified_fixed`

## Verification Results

- `./.venv/bin/python -m py_compile engine.py src/grounded_research/decompose.py src/grounded_research/collect.py src/grounded_research/source_quality.py src/grounded_research/tools/web_search.py src/grounded_research/models.py tests/test_tyler_v1_stage1_runtime.py tests/test_tyler_v1_stage2_runtime.py tests/test_collect.py tests/test_source_quality.py tests/test_web_search.py`
- `./.venv/bin/python -m pytest tests/test_tyler_v1_stage1_runtime.py tests/test_tyler_v1_stage2_runtime.py tests/test_collect.py tests/test_source_quality.py tests/test_web_search.py -q`
- `./.venv/bin/python -m pytest tests/test_engine_fixture_loading.py tests/test_phase_boundaries.py tests/test_engine.py -q`
