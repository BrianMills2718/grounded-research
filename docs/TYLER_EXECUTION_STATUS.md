# Tyler Execution Status

This is the strict status surface for Tyler's requested implementation.

Every item is classified as one of:

- **Required**: Tyler explicitly asked for it or the spec clearly depends on it.
- **Extension**: useful local capability not required by Tyler.
- **Blocked by shared infra**: still Tyler-required, but owned outside `grounded-research`.

## Required: Done

1. Tyler-native Stage 1-6 runtime contracts
2. Tyler-native Stage 1-6 export/handoff surfaces
3. Repo-local prompt literalness for Stage 1 through Stage 6
4. Tyler-style Stage 5 verification-query behavior (counterfactual patterns)
5. Tyler-native report/synthesis path in the live runtime
6. Tavily + Exa shared-provider search in the live runtime
7. Archived legacy behavior kept out of the live runtime path
8. Tyler-literal model assignments in default config (GPT-5.4, Claude Opus 4.6, Gemini 2.5 Pro)
9. Cheap testing config split (`config/config.testing.yaml`)
10. Deterministic URL lookup table for source quality scoring (Tyler §Stage 2)
11. String-template query generation (Tyler §Stage 2: "not a model call")
12. Evidence label numeric weights (Tyler §Design #5: 1.0/0.8/0.5/0.3)
13. Verification query budget enforcement (Tyler §Stage 5: max 3 queries/dispute)
14. Tyler-literal quality_tier → numeric score mapping (1.0/0.7/0.5/0.3)

## Required: Still Open

1. Frontier-model runtime validation
   - Models are configured correctly but haven't been tested in a live run
   - Owner: shared model availability + config policy
2. Gemini strict-schema quality study
   - Owner: `llm_client` + `prompt_eval`
3. Broader frozen Tyler-vs-legacy evaluation coverage
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

## Policy

Use this rule when making changes:

1. implement Tyler-required items first
2. do not delete useful extensions unless they conflict with Tyler or create a
   second runtime family
3. document extensions as additive, not as if Tyler requested them
4. do not move shared-infra work back into `grounded-research`
