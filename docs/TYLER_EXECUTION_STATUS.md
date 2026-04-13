# Tyler Execution Status

This is the strict status surface for Tyler's requested implementation.

During the clause-by-clause audit wave, the canonical detailed source of truth
for open gaps is:

- `docs/TYLER_SPEC_GAP_LEDGER.md`

For the review-process root-cause analysis and the controls that now prevent
future parity overclaims, use:

- `docs/TYLER_AUDIT_FAILURE_ANALYSIS.md`

Every item is classified as one of:

- **Required**: Tyler explicitly asked for it or the spec clearly depends on it.
- **Extension**: useful local capability not required by Tyler.
- **Blocked by shared infra**: still Tyler-required, but owned outside `grounded-research`.

## Required: Done

1. Tyler-native Stage 1-6 runtime contracts
2. Tyler-native Stage 1-6 export/handoff surfaces
3. Tyler-native report/synthesis path in the live runtime
4. Tavily + Exa shared-provider search in the live runtime
5. Archived legacy behavior kept out of the live runtime path
6. Cheap testing config split (`config/config.testing.yaml`)
7. Deterministic URL lookup table for source quality scoring (Tyler §Stage 2)
8. Evidence label numeric weights (Tyler §Design #5: 1.0/0.8/0.5/0.3)
9. Verification query budget enforcement (Tyler §Stage 5: max 3 queries/dispute)
10. Tyler-literal quality_tier → numeric score mapping (1.0/0.7/0.5/0.3)
11. Stage 5 hard round cap
12. Stage 5 prompt-order randomization
13. Stage 6a user-steering sequencing against the post-Stage-5 queue
14. Stage 4 prompt-order randomization
15. Stage 6 evidence-context completeness
16. Stage 6 context-compaction parity
17. Stage 6 non-dominant synthesis-model policy
18. Default Stage 3 B/C frame-model mapping following the Prompt packet's
    explicit assignment
19. Stage 1 no-validation parity
21. Stage 2 Tavily/Exa routing-by-query-type
22. Stage 2 literal quality-score pipeline
23. Stage 5 exact verification-query role parity
24. Stage 5 structured search-parameter execution
25. Stage 2 Tavily search-depth parity
26. Stage 2 Exa routing/control parity
27. Gemini strict-schema study and direct-Gemini thinking-budget fix landed in shared infra (`llm_client/main` via PR #27 / `e9a0cbf`)
28. Exact Tyler Gemini model-version parity
   - Shared registry parity landed in `llm_client/main` via PR #28 / `37623ec`.
   - The live config now points Tyler's named Gemini roles at `openrouter/google/gemini-3.1-pro-preview`.
   - Raw-question validation run `output/tyler_exact_model_version_switch_wave1_palantir` completed successfully and its run-local observability DB proves:
     - `question_decomposition_tyler_v1` used `openrouter/google/gemini-3.1-pro-preview`
     - `finding_extraction_tyler_v1` used `openrouter/google/gemini-3.1-pro-preview`
     - Analyst B `analyst_reasoning_tyler_v1` used `openrouter/google/gemini-3.1-pro-preview`
     - `query_diversification_tyler_v1` intentionally remained on `openrouter/google/gemini-2.5-pro`

## Required: Active Implementation Gaps

1. Stage 2 query variant generation
   - Exhaustive packet audit reopened this row.
   - Tyler's Build Plan and Prompt packet both specify orchestrator-expanded
     string templates, not an LLM call.
   - The live runtime still uses `acall_llm_structured(...)` plus
     `prompts/tyler_v1_query_diversification.yaml`.
   - Canonical row: `S2-QUERY-MODEL-001`

2. Stage 6 grounding reject-and-retry
   - Tyler's Schema packet says post-synthesis grounding failures should
     reject and retry once.
   - The live runtime validates grounding only after Stage 6 completes and
     currently records failures as warnings while still writing the report.
   - Canonical row: `S6-GROUNDING-001`

## Operational Watch

1. Frontier-model runtime / model-policy watch item
   - Three literal production-config fixture runs are recorded. The first failed the Claude Opus Stage 3 citation quality floor; the next two passed cleanly on the same primary-model stack.
   - Frontier Reliability Wave 3 showed the miss was a clean model output with one uncited claim (`C-16`), not a transport, schema, or local orchestration defect.
   - This is no longer treated as an active implementation blocker. It is a documented watch item governed by the explicit threshold in `docs/plans/tyler_frontier_model_policy_wave1.md`.
   - Reopen only if the same model-role pair fails the same quality floor in `2/3` identical reruns, the same failure mode appears on `2` distinct fixtures, or a shared runtime defect is proven.
   - Evidence: `output/tyler_frontier_runtime_validation_wave1`, `output/tyler_frontier_runtime_validation_wave2_repeat`, and `output/tyler_frontier_runtime_validation_wave2_palantir`
## Required: Explicit Tyler Ambiguity

1. Stage 2 shared output block vs `Finding` schema
   - Tyler's shared output instructions imply a reasoning field everywhere.
   - Tyler's Stage 2 `Finding` schema does not include a reasoning field.
   - Current repo preserves Tyler's schema and documents the conflict explicitly.
   - Canonical row: `AMB-S2-REASONING-001`

2. Stage 3 frame assignment packet conflict
   - Tyler's Build Plan assigns Claude Opus to `structured_decomposition` and
     Gemini to `verification_first`.
   - Tyler's Prompt packet assigns Gemini to `structured_decomposition` and
     Claude Opus to `verification_first`, and calls out the discrepancy
     explicitly.
   - Current repo follows the Prompt packet assignment.
   - Canonical row: `AMB-S3-FRAME-001`

## Extension: Present But Not Tyler-Required

These may remain if they do not conflict with Tyler and are documented as
additive behavior rather than Tyler requirements.

1. dense dedup / canonicalization hardening
2. sectioned synthesis for long thorough-mode reports
3. export repair loops for underfilled decision fields
4. broader benchmark harness and frozen-eval workflow
5. depth-mode execution beyond Tyler's original framing
6. additive Stage 4/5 lineage fields tracked in `tyler_v1_models.py`

## Policy

Use this rule when making changes:

1. implement Tyler-required items first
2. do not delete useful extensions unless they conflict with Tyler or create a
   second runtime family
3. document extensions as additive, not as if Tyler requested them
4. do not move shared-infra work back into `grounded-research`
5. if this status note and the ledger disagree, trust the ledger

## Eval Gate: Satisfied For Current Lane

Frozen Tyler-vs-legacy coverage is sufficient for the current implementation
lane.

Current evidence:

- UBI: Tyler `0.85` vs legacy `0.6833`
- PFAS: Tyler `0.7333` vs legacy `0.4333`
- LLM SWE: Tyler `0.9167` vs legacy `0.75`

Use this evidence as:

- a regression gate,
- directional proof that Tyler-literal is not underperforming archived
  calibrated legacy,
- and enough breadth for current implementation work.

Do not treat broader frozen-eval expansion as the next default blocker unless a
later implementation wave needs more coverage.
