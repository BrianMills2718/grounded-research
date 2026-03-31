# Tyler Shared Infra Ownership

This note names the remaining non-local Tyler gaps and their owning shared
infrastructure surfaces.

## Ownership Map

| Gap | Owner | Current surface |
|---|---|---|
| Exa provider parity Tyler assumed for Stage 2/5 | `open_web_retrieval` | shipped on `open_web_retrieval/main` via Plan #11; `grounded-research` now consumes Exa through the shared-provider search tool when configured |
| Runtime durability defaults and trace-query support for long structured calls | `llm_client` | merged on `llm_client/main` via Plan 21 |
| Frozen Tyler-vs-legacy saved-output comparison path | `prompt_eval` | merged on `prompt_eval/main` via Plan 11 |
| Gemini strict-schema quality study | `llm_client` + `prompt_eval` | not closed yet; remains an explicit shared follow-up rather than a local repo TODO |
| Exact frontier-model role parity from Tyler's original stack | shared model availability + config surfaces | not a repo-local implementation task in `grounded-research` |

## Boundary Rule

`grounded-research` should not reopen local runtime branches to chase these
gaps. The only justified local work after repo-local cutover is:

- consuming shared-infra improvements,
- running new frozen comparisons,
- or fixing a benchmark-proven repo-local defect.
