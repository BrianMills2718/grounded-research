# Plan: Wave 2 Runtime Reliability and Benchmark Completion

`docs/PLAN.md` remains the canonical repo-level plan. This file is the
executable implementation plan for the runtime-reliability slice that now
blocks Wave 2 benchmark completion.

**Status:** Planned
**Type:** implementation
**Priority:** High
**Blocked By:** None
**Blocks:** End-to-end Wave 2 benchmark completion and reliable overnight runs

---

## Gap

**Current:** The pipeline method is stable enough to benchmark, but long runs
still fail or stall for operational reasons:

- `sqlite3.OperationalError: database is locked` when multiple workloads share
  the default `llm_client` observability SQLite database
- late-stage provider hangs on long structured calls during claim extraction,
  arbitration, and synthesis

**Target:** A benchmark-safe runtime policy that makes full long runs finish
reliably in the standard dev environment without changing the cheap-model
baseline.

**Why:** The next gate is not another prompt tweak. It is proving that the
current method can complete real benchmark runs consistently enough to measure.

---

## References Reviewed

- `CLAUDE.md` - project operating rules, especially shared runtime/config policy
- `docs/PLAN.md` - canonical execution plan and current execution topology
- `docs/plans/wave2_enumeration_grounding.md` - active quality-recovery wave
- `docs/TECH_DEBT.md` - runtime failures already observed in real UBI runs
- `engine.py` - run entrypoints and output-dir ownership
- `src/grounded_research/config.py` - current operational policy surface
- `src/grounded_research/decompose.py` - decomposition LLM calls
- `src/grounded_research/collect.py` - query generation and source scoring calls
- `src/grounded_research/analysts.py` - analyst call entrypoint
- `src/grounded_research/canonicalize.py` - claim extraction, dedup, disputes
- `src/grounded_research/verify.py` - arbitration and verification queries
- `src/grounded_research/export.py` - report generation and long-form synthesis
- `~/projects/llm_client/llm_client/core/client.py` - public timeout surface
- `~/projects/llm_client/llm_client/execution/timeout_policy.py` - timeout-policy behavior
- `~/projects/llm_client/llm_client/io_log.py` - `LLM_CLIENT_DB_PATH` support

---

## Files Affected

- `config/config.yaml` (modify)
- `src/grounded_research/config.py` (modify)
- `src/grounded_research/runtime_policy.py` (create)
- `engine.py` (modify)
- `src/grounded_research/decompose.py` (modify)
- `src/grounded_research/collect.py` (modify)
- `src/grounded_research/analysts.py` (modify)
- `src/grounded_research/canonicalize.py` (modify)
- `src/grounded_research/verify.py` (modify)
- `src/grounded_research/export.py` (modify)
- `tests/test_runtime_policy.py` (create)
- `tests/test_verify.py` (modify)
- `tests/test_canonicalize.py` (modify)
- `tests/test_collect.py` (modify)
- `docs/TECH_DEBT.md` (modify)

---

## Pre-Made Decisions

1. Reliability policy lives in project config, not shell scripts.
2. Raw-question and fixture runs both get run-local observability DBs by
   default, stored under the run output directory.
3. `LLM_CLIENT_TIMEOUT_POLICY` is set explicitly to `allow` for pipeline runs.
4. Long but finite request timeouts are passed explicitly through
   `llm_client` call sites.
5. This wave fixes runtime reliability in `grounded-research` first rather
   than waiting for a broader `llm_client` redesign.
6. If a long benchmark still fails after this slice, the remaining blocker must
   be documented in `TECH_DEBT.md` and tied to a trace/output artifact.

---

## Plan

### Steps

1. Add a run-runtime policy section to `config/config.yaml`.
   Include:
   - `use_run_local_observability_db`
   - `timeout_policy`
   - per-task request timeouts

2. Create a small runtime-policy helper module.
   It should:
   - derive the run-local SQLite path from `output_dir`
   - set process env before the first `llm_client` call
   - reconfigure `llm_client` logging in-process if `llm_client` is already imported
   - expose typed timeout lookups by task name

3. Wire runtime policy at the top of both engine entry paths.
   Both `run_pipeline()` and `run_pipeline_from_question()` must configure the
   run-local DB path and timeout policy before collection/LLM work begins.

4. Pass explicit per-task request timeouts into the real call sites.
   Apply to:
   - decomposition
   - query generation
   - source scoring
   - analyst runs
   - claim extraction
   - dedup
   - dispute classification
   - verification query generation
   - arbitration
   - structured synthesis
   - long-form synthesis

5. Add targeted tests for runtime-policy behavior and timeout propagation.

6. Update `TECH_DEBT.md` after verification.
   Narrow the old blocker language if this slice resolves the DB-lock / timeout
   issues in the repo-local runtime policy.

---

## Failure Modes

| Failure Mode | Detection | Response |
|--------------|-----------|----------|
| Run-local DB policy is configured too late | tool-call / llm rows still hit the shared default DB | move runtime configuration earlier in engine entrypoints and verify with a test |
| Timeout policy is set but call sites still inherit defaults | monkeypatched `acall_llm*` tests show missing `timeout=` kwargs | patch the missing stage directly instead of assuming a global wrapper caught it |
| Finite timeouts are too short and create false failures | benchmark fails quickly with timeout errors on healthy phases | increase per-task config values; do not revert to unbounded waits |
| Only fixture runs get the safer runtime policy | raw-question path still writes to shared DB or hangs | configure both entry paths through the same helper |

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_runtime_policy.py` | `test_configure_run_runtime_sets_run_local_db_path` | run-local DB path is derived from the output dir |
| `tests/test_runtime_policy.py` | `test_get_request_timeout_reads_configured_task_timeout` | runtime policy exposes typed timeout lookup |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/test_collect.py` | query generation / source scoring still work with explicit timeout kwargs |
| `tests/test_canonicalize.py` | claim extraction / dedup still receive the expected call contract |
| `tests/test_verify.py` | arbitration remains protocol-valid while using explicit timeouts |
| `tests/test_phase_boundaries.py` | end-to-end phase contracts remain stable |

---

## Acceptance Criteria

- [ ] Both engine entry paths configure a run-local observability DB by default
- [ ] All long-running `llm_client` call sites use config-driven finite request timeouts
- [ ] Targeted tests pass
- [ ] Phase-boundary tests pass
- [ ] `TECH_DEBT.md` is updated to reflect the new runtime policy

---

## Notes

- This wave is intentionally operational. It is not a model-method change.
- Do not add another observability backend here; use the existing `llm_client`
  runtime and the already-landed `tool_calls` surface.
