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
18. Default Stage 3 B/C frame-model mapping
19. Stage 1 no-validation parity
20. Stage 2 model-driven query diversification
21. Stage 2 Tavily/Exa routing-by-query-type
22. Stage 2 literal quality-score pipeline
23. Stage 5 exact verification-query role parity

## Required: Still Open

1. Stage 2 Tavily search-depth parity
   - Tyler uses Tavily `basic` for default Stage 2 queries, but shared search is hardcoded to `advanced` and cannot yet express the routing table.
   - Owner: `open_web_retrieval`
2. Stage 2 Exa routing/control parity
   - Tyler expects semantic/deep routing plus Exa-specific `systemPrompt` and academic category controls, but shared Exa search cannot yet express those knobs.
   - Owner: `open_web_retrieval`
3. Frontier-model runtime validation
   - Models are configured approximately but haven't been tested in a fully literal live run.
   - Owner: shared model availability + config policy
4. Gemini strict-schema quality study
   - Owner: `llm_client` + `prompt_eval`
5. Broader frozen Tyler-vs-legacy evaluation coverage
   - Owner: `prompt_eval` + saved benchmark artifacts

## Required: Explicit Tyler Ambiguity

1. Stage 2 shared output block vs `Finding` schema
   - Tyler's shared output instructions imply a reasoning field everywhere.
   - Tyler's Stage 2 `Finding` schema does not include a reasoning field.
   - Current repo preserves Tyler's schema and documents the conflict explicitly.

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
