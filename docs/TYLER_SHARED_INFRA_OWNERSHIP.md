# Tyler Shared Infra Ownership

This note names the remaining non-local Tyler gaps and their owning shared
infrastructure surfaces.

## Ownership Map

| Gap | Owner | Current surface |
|---|---|---|
| Runtime durability defaults and trace-query support for long structured calls | `llm_client` | merged on `llm_client/main` via Plan 21 |
| Frozen Tyler-vs-legacy saved-output comparison path | `prompt_eval` | merged on `prompt_eval/main` via Plan 11 |
| Gemini strict-schema quality study | `llm_client` + `prompt_eval` | merged on `llm_client/main` via PR #27 (`e9a0cbf`): Plan 26 recorded the direct-vs-OpenRouter evidence and Plan 27 replaced the hardcoded direct-Gemini `budget_tokens=0` default with shared config. This is no longer an open blocker for `grounded-research`; any future `prompt_eval` use is optional follow-through, not a required closure step |
| Exact Tyler Gemini model-version parity | shared model registry + config surfaces | Tyler names Gemini 3.1 Pro, while the live config still uses `openrouter/google/gemini-2.5-pro`. OpenRouter currently exposes `google/gemini-3.1-pro-preview`, and shared follow-through is now active on `llm_client` PR #28: Plan 28 adds the model to the packaged registry and records `5/5` Tyler-like native-schema successes in `docs/reviews/2026-04-09-openrouter-gemini31-pro-validation.json`. This row stays open until that shared PR lands and `grounded-research` switches to the exact model surface |
| Frontier-model runtime/model-policy reliability | shared model availability + config surfaces | three literal production-config runs are now recorded; Frontier Reliability Wave 3 showed the failed PFAS run was a clean Claude Opus Stage 3 response with one uncited claim, while the next PFAS repeat and the Palantir run passed. The remaining issue is now best classified as model-output variability / model-policy limitation rather than a `llm_client` transport defect or a repo-local bug. Current policy: keep the Tyler-intended primary stack unless the same failure repeats in `2/3` identical reruns, appears on `2` distinct fixtures, or a shared runtime defect is proven |

## Boundary Rule

`grounded-research` should not reopen local runtime branches to chase these
gaps. The only justified local work after repo-local cutover is:

- consuming shared-infra improvements,
- running new frozen comparisons,
- or fixing a benchmark-proven repo-local defect.

Shared retrieval controls for search depth, chunk budget, corpus/category, and
structured domain filters are already shipped in `open_web_retrieval` via Plan
#15, and generic retrieval-instruction support is shipped via Plan #16. These
are no longer blockers by themselves.
