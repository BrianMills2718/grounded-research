# Scope Matrix V2

This matrix aligns the project plan with the adjudication-first decision in
`docs/adr/0001-adjudication-first-scope.md`.

It separates three categories:

1. core work for the smallest falsifiable slice
2. deferred capabilities that remain part of the plan
3. items still cut for now

## Core Now

These support the thesis-proving slice and should stay on the critical path:

- upstream evidence ingest rather than a new retrieval stack
- three independent analyst runs over shared evidence
- claim extraction and semantic deduplication
- canonical claim ledger construction
- typed dispute detection and deterministic routing
- narrow verification for factual and interpretive conflicts
- grounded export with trace and downstream handoff

## Deferred But Retained

These are valuable and should remain visible in planning, but they do not need
to block the smallest useful version:

- `ambiguity` dispute user-clarification routing (the type exists in the
  schema and routes to `surface`; what's deferred is interactive user
  clarification before arbitration)
- a canonical `AssumptionLedger` or equivalent first-class assumption state
- stronger fixed reasoning frames:
  - `verification_first`
  - `structured_decomposition`
  - `step_back_abstraction`
- persistent Stage `1v` caveats and warnings in pipeline state
- a hard arbitration rule limiting claim revisions to:
  - new evidence
  - corrected assumptions
  - resolved contradictions
- an explicit assumptions section in the final report
- a validator that prevents settled disputes from reappearing as unresolved report conflicts

## Cut For Now

These remain out of scope unless new traces show clear need:

- a new planner-first pipeline inside this repo
- a new production retrieval stack inside this repo
- novelty or diminishing-returns stopping logic
- runtime evidence-laundering detection beyond structural checks
- Grok or X-specific integration
- broad runtime anti-bias instrumentation
- elaborate planner validation-and-retry loops
- broad user-steering flows before the core adjudication slice works

## Design Reminder

The project should still default to:

- LLMs for semantic tasks
- deterministic code for mechanical enforcement
- recent-first evidence policy for time-sensitive questions
- fail-loud trace-preserving behavior

The claim ledger remains the product. The report remains a rendering of that
state.
