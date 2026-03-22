# ADR 0004: Phase 4 Agentic Verification and Fail-Loud Boundaries

## Status

Accepted

## Date

2026-03-22

## Context

This repo’s adjudication layer is designed to prove value through
decision-critical dispute resolution, not just claim aggregation. Earlier
implementation had gaps that prevented full end-to-end thesis delivery:

- dispute arbitration can run without proving fresh evidence was retrieved;
- `verify_disputes` bypasses the query-generation path and resolves directly from
  already-imported evidence;
- some failure branches are too silent to support auditable diagnostics.

The project’s quality-first requirement therefore demands that Phase 4 actually
execute evidence refresh and that contract violations fail loudly with structured
trace context.

### Update (2026-03-22)

The v1 implementation now satisfies the core ADR-0004 constraints through a
structured `Phase 4a`/`4b` flow:

- batch query generation for all routed decision-critical disputes;
- dispute-specific fresh evidence retrieval in `_collect_fresh_evidence_for_dispute`;
- arbitration against fresh evidence with mandatory `new_evidence_ids` for
  non-`inconclusive` outcomes;
- explicit `adjudicate` warning persistence in phase traces when partial
  verification failures occur.

The agentic single-loop execution path remains a planned convergence step, not a
current invariant.

## Decision

1. **Phase 4 must perform evidence-aware arbitration**
   - A decision-critical dispute is advanced only after dispute-specific evidence
     retrieval steps are executed.
   - The default v1 path remains:
     1. generate `VerificationQueryBatch` for each targeted dispute;
     2. search + read candidate sources;
     3. persist newly discovered `EvidenceItem`s;
     4. arbitrate on the original plus newly retrieved evidence.
   - The output contract stays unchanged (`ArbitrationResult` + updated ledger),
     but `new_evidence_ids` must be populated for any non-`inconclusive`
     verdict.

2. **Fail-loud is mandatory at phase boundaries**
   - `EvidenceBundle` parsing/normalization errors are surfaced as explicit
     failures with file path, offending payload fragment, and parse stage in
     context.
   - Dispute arbitration failures emit warnings or abort according to phase
     criticality:
     - verification path errors are persisted in the pipeline trace as warnings
       and allow the pipeline to continue when at least one dispute remains
       resolvable;
     - schema-breaking/contract-breaking failures fail the phase and preserve
       partial trace.

3. **Evidence freshness is treated as a first-class invariant**
   - Arbitration outcomes with `verdict` in
     `{"supported", "revised", "refuted"}` must explain which evidence is new.
   - `Dispute.resolved` is set only when arbitration is completed with
     non-empty evidence-driven rationale.

4. **Complexity is acceptable where it improves adjudication quality**
   - Phase 4 remains in an `llm_client`-compatible shape, but uses tool-aware
     execution paths where needed.
   - Existing retrieval/fetch tooling (`brave_search`, `fetch_page`,
     `jina_reader`) is the preferred base; no greenfield web stack.

## Consequences

- The adjudication thesis becomes falsifiable again because dispute outcomes can
  now change based on actual supplementary evidence.
- `verify_disputes` now owns the boundary between “claim conflict” and
  “resolved/reframed conflict” with deterministic evidence provenance.
- Partial-failure handling becomes more operationally expensive to implement, but
  materially reduces silent correctness regressions.
- Downstream consumers can inspect phase-local evidence provenance through the
  trace and `claim_updates`.

## Follow-On Rules

1. Preserve the v1 structured-call stepping stones (`Phase 4a/4b`) as a fallback
   path while agentic orchestration hardens.
2. Keep `ArbitrationResult` schema unchanged; require stronger execution semantics
   in orchestration code instead of changing the contract.
3. Add/update tests for:
   - arbitration requiring fresh evidence,
   - schema/parsing failures producing loud and actionable diagnostics,
   - trace continuity on partial failure.
4. Preserve explicit phase-local LLM-call accounting for planning dashboards and
   post-mortem interpretation.

## Machine-Readable Invariants

```yaml
invariants:
  - id: adr4_phase4a_query_batch
    must_hold: "verify_disputes generates VerificationQueryBatch for each routed decision-critical dispute before arbitration."
    source_of_truth:
      - src/grounded_research/verify.py
      - docs/PLAN.md
      - docs/adr/0004-agentic-verification-and-fail-loud-phase4.md
    checks:
      - file: src/grounded_research/verify.py
        must_include:
          - "generate_verification_queries("
          - "query_lookup"
          - "actionable"
  - id: adr4_fresh_evidence_backing
    must_hold: "Any non-inconclusive ArbitrationResult must include >=1 new_evidence_id that came from fresh retrieval."
    source_of_truth:
      - src/grounded_research/verify.py
      - prompts/arbitration.yaml
      - src/grounded_research/models.py
    checks:
      - file: src/grounded_research/verify.py
        must_include:
          - "fresh_evidence_ids"
          - "if result.verdict in {\"supported\", \"revised\", \"refuted\"}"
          - "new_evidence_ids"
      - file: prompts/arbitration.yaml
        must_include:
          - "Fresh Evidence Candidate Set"
          - "new_evidence_ids"
  - id: adr4_fail_loud_warnings
    must_hold: "Partial verification failures are surfaced as adjudicate warnings in PipelineState.trace."
    source_of_truth:
      - engine.py
      - src/grounded_research/verify.py
      - src/grounded_research/models.py
      - docs/adr/0004-agentic-verification-and-fail-loud-phase4.md
    checks:
      - file: engine.py
        must_include:
          - "state.add_warning(\"adjudicate\""
          - "phase4_llm_calls"
      - file: src/grounded_research/models.py
        must_include:
          - "PhaseTrace"
  - id: adr4_llm_call_accounting
    must_hold: "Phase 4 phase trace llm_calls reflects query-generation plus arbitration calls."
    source_of_truth:
      - engine.py
      - src/grounded_research/verify.py
      - src/grounded_research/models.py
    checks:
      - file: engine.py
        must_include:
          - "phase4_llm_calls"
          - "llm_calls=phase4_llm_calls"
      - file: src/grounded_research/verify.py
        must_include:
          - "llm_calls = 0"
          - "llm_calls + 1"
```

```bash
# CI check (strict):
python scripts/check_adr_invariants.py \
  --adr docs/adr/0004-agentic-verification-and-fail-loud-phase4.md \
  --strict
```

```bash
# Generate checklist only:
python scripts/check_adr_invariants.py \
  --adr docs/adr/0004-agentic-verification-and-fail-loud-phase4.md \
  --skip-pattern-checks
```
