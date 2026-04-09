# Tyler Shared Infra Ownership

This note names the remaining non-local Tyler gaps and their owning shared
infrastructure surfaces.

## Ownership Map

| Gap | Owner | Current surface |
|---|---|---|
| Runtime durability defaults and trace-query support for long structured calls | `llm_client` | merged on `llm_client/main` via Plan 21 |
| Frozen Tyler-vs-legacy saved-output comparison path | `prompt_eval` | merged on `prompt_eval/main` via Plan 11 |
| Gemini strict-schema quality study | `llm_client` + `prompt_eval` | active shared closure path now exists as `llm_client` PR #27 (`gemini-schema-main-merge` @ `e9a0cbf`): Plan 26 recorded the direct-vs-OpenRouter evidence and Plan 27 replaced the hardcoded direct-Gemini `budget_tokens=0` default with shared config; still pending PR merge and any follow-on `prompt_eval` use |
| Exact frontier-model role parity from Tyler's original stack | shared model availability + config surfaces | three literal production-config runs are now recorded; the first exposed a Claude Opus Stage 3 citation-floor failure, while the next two passed, so the remaining issue is intermittent frontier reliability rather than a clean repo-local defect |

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
