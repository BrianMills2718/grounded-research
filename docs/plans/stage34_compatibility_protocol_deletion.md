# Stage 3/4 Compatibility Protocol Deletion

**Status:** In Progress
**Purpose:** Delete the dead current-shape Stage 3/4 utility path so the repo
keeps one canonical Stage 4 vocabulary.

## Why This Plan Exists

After the Stage 5 internal protocol cutover, the remaining current-shape
runtime debt is concentrated in dead utility code:

- `canonicalize.py` still exports `deduplicate_claims()` and `detect_disputes()`
- `models.py` still defines `RawClaim`, current `Claim`, current `Dispute`,
  and related Stage 3/4 helper models/enums
- the live runtime does not call that path; only historical tests do

This is no longer migration scaffolding that protects the product. It is dead
parallel vocabulary in the core reasoning area.

## Canonical Decisions

1. Tyler `ClaimExtractionResult` is the only canonical Stage 4 artifact in
   `main`.
2. Dead Stage 3/4 compatibility utilities are deleted, not hidden behind
   config or moved behind a fallback path.
3. Tests that only prove deleted compatibility utilities are removed.
4. Historical comparison behavior is preserved by commits and benchmark
   artifacts, not by retaining a second Stage 4 path in the runtime tree.

## Acceptance Criteria

This wave is complete only if:

1. `canonicalize.py` no longer exports `deduplicate_claims()` or
   `detect_disputes()`
2. `models.py` no longer defines the dead current-shape Stage 3/4 semantic
   models and routing table:
   - `RawClaim`
   - current `Assumption`
   - current `Recommendation`
   - current `Counterargument`
   - current `Claim`
   - current `Dispute`
   - current `ClaimStatus`, `DisputeType`, `DisputeRoute`
   - `DISPUTE_ROUTING`
3. Tyler Stage 4 canonicalization tests still pass
4. active docs describe Tyler Stage 4 as the only shipped Stage 4 contract

## Ordered Phases

### Phase 1: Delete dead canonicalize helpers

- remove `deduplicate_claims()`
- remove `detect_disputes()`
- remove now-unused imports and comments tied to the deleted path

Files:

- `src/grounded_research/canonicalize.py`
- `tests/test_canonicalize.py`

### Phase 2: Delete dead current-shape Stage 3/4 models

- remove the current-shape Stage 3/4 semantic models and enum/routing helpers
- keep `SourceRecord`, `EvidenceItem`, `EvidenceBundle`, `ResearchQuestion`,
  `DecompositionValidation`, `Stage3AttemptTrace`, `PipelineState`, and any
  still-live general support models

Files:

- `src/grounded_research/models.py`
- `tests/test_tyler_v1_models.py` if any current-shape imports remain

### Phase 3: Rewrite authority docs and commit map

- update `docs/CONTRACTS.md`, `docs/PLAN.md`, `docs/ROADMAP.md`,
  `docs/ARCHITECTURE_ONE_PAGE.md`, `docs/DOMAIN_MODEL.md`,
  `docs/TYLER_LITERAL_PARITY_AUDIT.md`, `docs/TYLER_VARIANT_COMMIT_MAP.md`,
  and the plan index
- record the last commit that still contained the dead Stage 3/4 compatibility
  utility path

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| A deleted Stage 4 helper still backs a hidden runtime path | canonicalization or phase-boundary tests fail outside the old compatibility tests | restore only the minimal behavior needed for the live Tyler path, not the deleted helper API |
| Test coverage drops below live Stage 4 needs | only old dedup tests were proving something still live | replace with Tyler Stage 4 tests rather than restoring current-shape utilities |
| Docs still imply dual Stage 4 contracts | active docs mention current `Claim`/`Dispute` as live | rewrite immediately; do not leave mixed vocabulary in active docs |
