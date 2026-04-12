# Tyler Shared Infra Ownership

This note names the remaining non-local Tyler gaps and any shared operational
watch items.

## Ownership Map

| Gap | Owner | Current surface |
|---|---|---|
| Runtime durability defaults and trace-query support for long structured calls | `llm_client` | merged on `llm_client/main` via Plan 21 |
| Frozen Tyler-vs-legacy saved-output comparison path | `prompt_eval` | merged on `prompt_eval/main` via Plan 11 |
| Gemini strict-schema quality study | `llm_client` + `prompt_eval` | merged on `llm_client/main` via PR #27 (`e9a0cbf`): Plan 26 recorded the direct-vs-OpenRouter evidence and Plan 27 replaced the hardcoded direct-Gemini `budget_tokens=0` default with shared config. This is no longer an open blocker for `grounded-research`; any future `prompt_eval` use is optional follow-through, not a required closure step |

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

## Active Shared Implementation Gaps

None.

## Operational Watch

Frontier-model runtime/model-policy reliability is now a shared watch item, not
an active implementation blocker:

- three literal production-config runs are recorded
- the failed PFAS run was a clean Claude Opus Stage 3 response with one
  uncited claim
- the next PFAS repeat and the Palantir run passed on the same primary stack
- current policy: keep the Tyler-intended primary stack unless the same
  failure repeats in `2/3` identical reruns, appears on `2` distinct fixtures,
  or a shared runtime defect is proven

## Recently Closed Shared Lane

Exact Tyler Gemini model-version parity is no longer open:

- `llm_client/main` now exposes `openrouter/google/gemini-3.1-pro-preview` via
  PR #28 / `37623ec`
- `grounded-research` consumed that shared surface in
  `docs/plans/tyler_exact_model_version_switch_wave1.md`
- raw-question validation run
  `output/tyler_exact_model_version_switch_wave1_palantir` completed
  successfully and proved the switched Gemini roles used the exact model
  surface on the live path
