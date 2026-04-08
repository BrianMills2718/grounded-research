# Tyler Remediation Phase 6: Stage 5 Query Roles And Search Controls

`docs/TYLER_SPEC_GAP_LEDGER.md` is the canonical evidence source. This child
wave exists because direct code review after Phase 5 found that the live Stage
5 query path still does not match Tyler, despite earlier status docs claiming
it was fixed.

**Status:** Completed
**Type:** implementation
**Priority:** Critical
**Blocked By:** `docs/TYLER_SPEC_GAP_LEDGER.md`
**Blocks:** truthful Stage 5 closure claims

---

## Goal

Bring live Stage 5 verification-query generation and execution into line with
Tyler's requested behavior using the shared retrieval controls that already
exist in `open_web_retrieval`.

This is not a new shared-infra wave. The needed controls are already exposed
through `grounded_research.tools.web_search.search_web()`. The remaining gap is
local consumption plus a stale overclaim in the ledger/status layer.

---

## Ledger Rows

- `S5-QUERY-ROLES-001`
- `S5-SEARCH-PARAMS-001`

---

## Scope

### In Scope

1. Replace the live Stage 5 limitations/refutation builder with Tyler's actual
   query roles:
   - neutral question
   - weaker-position support query
   - authoritative-source query
   - dated authoritative query only when time-sensitive
2. Introduce a typed local Stage 5 query-plan surface so query role and
   provider controls are explicit and testable.
3. Pass Tyler-required Stage 5 search controls through the shared search tool:
   - `search_depth="advanced"`
   - `result_detail="chunks"`
   - `detail_budget=3`
   - `domains_allow` when an authoritative domain is known
4. Remove string-level `site:` routing when the same constraint can be
   expressed as a structured provider filter.
5. Reconcile the gap ledger and status docs so they stop claiming this row was
   fixed before the runtime actually matched it.

### Out of Scope

- new `open_web_retrieval` contract expansion
- Exa-specific Stage 5 behavior
- broader arbitration redesign

---

## Pre-Made Decisions

1. Stage 5 gets a small typed local plan model instead of raw query strings.
   The plan must carry:
   - `query_text`
   - `query_role`
   - `search_depth`
   - `result_detail`
   - `detail_budget`
   - `domains_allow`

2. Stage 5 remains Tavily-backed through the shared `search_web()` path.
   Do not add a new local provider client.

3. The authoritative-domain signal should be passed through
   `domains_allow` when available. Only keep `site:` in the query text if a
   concrete runtime constraint forces it.

4. Query-role selection is deterministic:
   - weaker claim = less-supported claim by Stage 4 support counts
   - authoritative query = neutral dispute topic plus domain/class targeting
   - dated query only for `time_sensitive`

5. This wave must delete dead Stage 5 helper code and stale test expectations
   as it goes.

---

## Implementation Surfaces

### Runtime

- `src/grounded_research/verify.py`
- `src/grounded_research/models.py`

### Tests

- `tests/test_verify.py`
- any affected Stage 5 / phase-boundary tests

### Docs

- `docs/TYLER_SPEC_GAP_LEDGER.md`
- `docs/TYLER_EXECUTION_STATUS.md`
- `docs/plans/CLAUDE.md`
- `docs/plans/tyler_faithful_execution_remainder.md`

---

## Acceptance Criteria

This wave passes only if all of the following are true:

1. `_build_tyler_verification_queries()` no longer emits limitations/refutation
   patterns.
2. Stage 5 search execution uses structured shared controls:
   - advanced depth
   - chunks detail
   - detail budget 3
   - domain filters when authoritative domains are known
3. The authoritative query no longer relies only on embedded `site:` text when
   `domains_allow` can carry the same intent.
4. Tests prove:
   - Stage 5 query-role shape
   - dated query only for time-sensitive disputes
   - Stage 5 search control propagation into `search_web()`
5. `S5-QUERY-ROLES-001` and `S5-SEARCH-PARAMS-001` move to
   `verified_fixed`.
6. Docs stop falsely implying the old Stage 5 path was already literal.

---

## Verification

Minimum required verification:

1. targeted `tests/test_verify.py` coverage for:
   - query-role generation
   - search parameter propagation
2. at least one higher-level verification path that still passes through
   `verify_disputes_tyler_v1()`
3. `py_compile` on touched runtime/test files

---

## Failure Modes

1. Replacing the query text but still executing with generic `search_web()`
   defaults.
2. Passing structured domain filters while still leaving dead `site:` string
   logic in the live path.
3. Fixing the code but not correcting the false earlier closure claims.
4. Adding a free-form options bag instead of a typed Stage 5 plan surface.

---

## Exit Condition

This plan is complete when:

1. the live Stage 5 path emits Tyler query roles,
2. the live Stage 5 search path consumes the current shared retrieval controls,
3. the two Stage 5 ledger rows are updated with real verification evidence,
4. and the docs no longer overclaim prior closure.

---

## Outcome

Completed on 2026-04-08.

Landed behavior:

1. introduced typed `Stage5QueryPlan` objects for the live verification path
2. replaced the old limitations/refutation builder with Tyler's neutral,
   weaker-position support, authoritative-source, and optional dated roles
3. passed structured Stage 5 search controls through `search_web()`:
   - `provider_override="tavily"`
   - `search_depth="advanced"`
   - `result_detail="chunks"`
   - `detail_budget=3`
   - `domains_allow` for authoritative-domain queries
4. removed the Stage 5 `site:`-only routing assumption from the live
   authoritative query path
5. corrected the earlier false closure claim in the ledger/status layer

## Verification Results

- `./.venv/bin/python -m py_compile src/grounded_research/verify.py src/grounded_research/models.py tests/test_verify.py`
- `./.venv/bin/python -m pytest tests/test_verify.py -q`
- `./.venv/bin/python -m pytest tests/test_phase_boundaries.py tests/test_engine.py -q`
