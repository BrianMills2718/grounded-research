# Tyler Execution Status

This is the strict status surface for Tyler's requested implementation.

Every item is classified as one of:

- **Required**: Tyler explicitly asked for it or the spec clearly depends on it.
- **Extension**: useful local capability not required by Tyler.
- **Blocked by shared infra**: still Tyler-required, but owned outside `grounded-research`.

## Required: Done

1. Tyler-native Stage 1-6 runtime contracts
2. Tyler-native Stage 1-6 export/handoff surfaces
3. Repo-local prompt literalness for Stage 1 and Stage 2
4. Tyler-style Stage 5 verification-query behavior
5. Tyler-native report/synthesis path in the live runtime
6. Tavily + Exa shared-provider search in the live runtime
7. Archived legacy behavior kept out of the live runtime path

## Required: Still Open

1. Exact frontier-model role parity
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
