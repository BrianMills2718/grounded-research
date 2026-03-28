# Stage 5 Internal Protocol Literalization

**Status:** In Progress
**Purpose:** Remove the remaining current-shape internal protocol types from
the live Tyler Stage 5 path so `main` keeps one canonical runtime vocabulary.

## Why This Plan Exists

The public/runtime cutover is mostly complete:

- Tyler Stage 1-6 artifacts are the canonical persisted/exported outputs
- `QuestionDecomposition`, `AnalystRun`, and `ClaimLedger` are gone
- compatibility export/report surfaces are gone

What remains is narrower but still real:

- `verify.py` still uses current-shape `Dispute`, `ArbitrationResult`,
  `ClaimUpdate`, and `VerificationQueryBatch`
- `tyler_v1_adapters.py` still projects Tyler Stage 5 assessments into current
  arbitration artifacts for compatibility-era tests

That keeps a second internal vocabulary alive in the most reasoning-critical
phase. It is the last meaningful repo-local tractability issue under Tyler
canonical cutover.

## Canonical Decisions

1. Live Stage 5 logic should operate on Tyler `DisputeQueueEntry`,
   `ArbitrationAssessment`, and `VerificationResult` directly.
2. Search-query generation may use a narrow Tyler-native helper surface, but it
   must not reintroduce current-shape verification contracts.
3. Compatibility projections should be deleted, not wrapped behind config.
4. If a current-shape type remains only to support a historical test, delete or
   rewrite that test.
5. Quality-first behavior is preserved; this wave is contract deletion, not a
   runtime simplification.

## Acceptance Criteria

This wave is complete only if:

1. `verify.py` no longer imports or returns current-shape `Dispute`,
   `ArbitrationResult`, `ClaimUpdate`, or `VerificationQueryBatch` in the live
   Tyler Stage 5 path
2. Stage 5 fresh-evidence collection, arbitration, and protocol enforcement
   operate directly on Tyler Stage 4/5 models
3. `tyler_v1_adapters.py` no longer exports Stage 5 current-shape projection
   helpers
4. targeted verification/export/phase-boundary tests pass
5. active docs describe the remaining repo-local contract truthfully

## Ordered Phases

### Phase 1: Replace query-batch and dispute inputs

- rewrite verification query generation to consume `DisputeQueueEntry`
- replace `VerificationQueryBatch` with a Tyler-native local helper or plain
  structured dicts if a dedicated model adds no value
- keep query-count observability explicit for `VerificationResult.search_budget`

Files:

- `src/grounded_research/verify.py`
- `src/grounded_research/models.py`
- `tests/test_verify.py`

### Phase 2: Replace current-shape arbitration results

- make dispute arbitration return Tyler `ArbitrationAssessment`
- move protocol enforcement onto Tyler claim/dispute models directly
- delete current-shape `ArbitrationResult` / `ClaimUpdate` from the live path

Files:

- `src/grounded_research/verify.py`
- `src/grounded_research/models.py`
- `tests/test_verify.py`

### Phase 3: Delete Stage 5 compatibility projection helpers

- remove `tyler_assessment_to_current_arbitration()`
- rewrite or delete tests that only prove current-shape arbitration projection

Files:

- `src/grounded_research/tyler_v1_adapters.py`
- `tests/test_tyler_v1_stage5_6_adapters.py`

### Phase 4: Rewrite authority docs and commit map

- update `docs/CONTRACTS.md`, `docs/PLAN.md`, `docs/ROADMAP.md`,
  `docs/ARCHITECTURE_ONE_PAGE.md`, `docs/DOMAIN_MODEL.md`,
  `docs/TYLER_LITERAL_PARITY_AUDIT.md`, and `docs/TYLER_VARIANT_COMMIT_MAP.md`
- record the last commit that still contained the deleted Stage 5
  current-shape protocol

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| Tyler dispute protocol loses fail-loud checks | verification tests stop rejecting malformed updates or missing fresh evidence | port the existing protocol checks onto Tyler Stage 5 models directly; do not restore current-shape result models |
| Search-budget accounting becomes implicit | `VerificationResult.search_budget` no longer matches dispute queries used | keep explicit per-dispute query counts in the new helper surface and assert them in tests |
| A deleted compatibility helper still supports a real inspection need | tests or CLI output lose human-readable dispute summaries | rederive summaries from Tyler artifacts rather than restoring compatibility projections |
