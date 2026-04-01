# Plan: Replace Timeouts with Call Observability

**Status:** Planned
**Owner:** shared infrastructure (llm_client) + grounded-research consumer
**Date:** 2026-03-31

## Problem

Timeouts are a bad heuristic for LLM calls:
- They kill legitimate slow calls (complex structured output can take 60-120s)
- LiteLLM doesn't enforce them correctly for OpenRouter (known bug: litellm#16394)
- They hide the real problem: no visibility into what's happening during a call
- They cause silent data loss (partially-complete pipeline killed mid-phase)

The current grounded-research config has per-task timeouts (120-300s) that are
either too aggressive (kill good calls) or ineffective (LiteLLM ignores them).

## Design

### Principle

**Observe, don't kill.** The human or a budget cap decides when to stop. The
infrastructure's job is to make the current state visible.

### Architecture (3 layers)

#### Layer 1: llm_client — In-Flight Call Monitor (shared infrastructure)

Add to `llm_client/execution/`:

```python
class CallMonitor:
    """Tracks in-flight LLM calls and emits periodic status warnings."""

    def register_call(self, call_id: str, task: str, model: str, trace_id: str) -> None:
        """Record that a call started. Spawns a background warning timer."""

    def complete_call(self, call_id: str) -> None:
        """Record that a call finished (success or failure)."""

    def get_in_flight(self) -> list[InFlightCall]:
        """Return all currently running calls with elapsed time."""
```

Behavior:
- When a call starts, register it with the monitor
- Background asyncio task logs warnings at configurable intervals:
  `"[llm_client] Call {task} to {model} running for {elapsed}s (trace: {trace_id})"`
- Warning thresholds: 60s (info), 120s (warning), 300s (error)
- Thresholds configurable via `LLM_CLIENT_CALL_WARNING_THRESHOLDS`
- The monitor NEVER cancels calls — it only logs
- On call completion, stop the warning timer

Integration point: wrap the existing `acall_llm_structured()` and
`acall_llm()` entry points. No change to public API — callers don't need
to know about the monitor.

#### Layer 2: llm_client — Safety Timeout (already exists)

Keep the existing `safety_timeout_s()` (default 300s) as a dead-connection
detector ONLY. This is not a request timeout — it catches TCP-level hangs
where the server literally stopped responding. This is the correct use of
a timeout.

The key distinction:
- **Request timeout** (remove): "the LLM is taking too long to think"
- **Safety timeout** (keep): "the TCP connection is dead and no bytes will
  ever arrive"

#### Layer 3: grounded-research — Remove Request Timeouts

Changes to grounded-research:
1. Remove all `timeout=` kwargs from LLM calls in:
   - decompose.py
   - collect.py
   - analysts.py
   - canonicalize.py
   - verify.py
   - export.py
2. Remove `runtime_reliability.request_timeouts_s` from both configs
3. Remove `get_request_timeout()` from runtime_policy.py
4. Set `LLM_CLIENT_TIMEOUT_POLICY=ban` in the pipeline env to disable
   request-level timeouts globally
5. Keep `pipeline_max_budget_usd` as the real safety net

### What Stops Runaway Calls?

Three mechanisms, in order:
1. **Budget cap** (`pipeline_max_budget_usd`): if you've spent $5, stop.
   Already implemented.
2. **Safety timeout** (300s): catches dead TCP connections. Already in
   llm_client.
3. **Human intervention**: Ctrl+C. The partial trace is always saved.

### What Does NOT Stop Calls

- Per-task request timeouts (removed)
- Automatic retry-then-give-up on slow calls (removed — retries only on
  actual errors)

## Acceptance Criteria

1. grounded-research pipeline runs with `LLM_CLIENT_TIMEOUT_POLICY=ban`
   and no `timeout=` kwargs
2. When a call takes >60s, a warning is logged (visible in terminal)
3. When a call takes >120s, a louder warning is logged
4. Pipeline completes end-to-end even when individual calls take 90-180s
5. Budget cap still enforced
6. Partial trace still saved on Ctrl+C / abort

## Implementation Order

### Phase 1: grounded-research (this repo)
- Remove `timeout=` kwargs from all LLM call sites
- Remove `request_timeouts_s` config section
- Remove `get_request_timeout()` helper
- Set env default to `LLM_CLIENT_TIMEOUT_POLICY=ban`
- Test: pipeline runs without timeouts

### Phase 2: llm_client (separate session)
- Add `CallMonitor` to `execution/`
- Integrate into `acall_llm_structured()` and `acall_llm()`
- Add `LLM_CLIENT_CALL_WARNING_THRESHOLDS` env config
- Test: warnings fire at correct intervals
- Keep `safety_timeout_s()` as dead-connection detector

### Phase 3: Validation
- Run grounded-research end-to-end with monitoring
- Verify warnings are visible and useful
- Verify budget cap catches runaway spend

## Risks

- **Without request timeouts, a truly hung call blocks the pipeline.**
  Mitigated by safety_timeout_s (300s) which catches dead connections.
  A legitimately slow but progressing call is allowed to complete.

- **Budget enforcement happens post-call, not mid-call.** A single
  expensive call could exceed budget before the cap fires. Mitigated
  by the safety timeout on dead connections. For legitimate calls, the
  budget cap applies to the aggregate, not individual calls.

## References

- llm_client timeout_policy.py: existing safety_timeout_s + policy toggle
- LiteLLM bug: https://github.com/BerriAI/litellm/issues/16394
- grounded-research TECH_DEBT.md: provider hang documentation
