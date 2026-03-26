# Tyler V1 -> Current Repo Map

This note maps Tyler's V1 package in `tyler_response_20260326/` to the current
`grounded-research` repo.

Use it as a boundary document:

- Tyler's V1 package is a reference architecture and prompt/schema package.
- The current repo is an already-built adjudication-centered system with its
  own shipped contracts and benchmark history.
- Not every divergence is a bug.

## What Already Aligns

These Tyler V1 ideas are already true in the current repo:

- raw question -> decomposition -> collection -> adjudication is supported
- imported evidence bundles are supported
- independent analyst passes over shared evidence are central to the pipeline
- a canonical claim ledger is the main analytical artifact
- dispute detection and routing are first-class
- targeted fresh-evidence arbitration exists
- user steering for ambiguity/preference disputes exists
- prompt hardening, Claimify-style extraction, anti-conformity enforcement,
  anonymization scrubbing, and dense canonicalization hardening were all landed
  during the Tyler-alignment waves

## Intentional Divergences

These differences are deliberate or currently acceptable:

### 1. Adjudication thesis over provider parity

Tyler's V1 locks Stage 2/5 around Tavily + Exa.

The current repo is judged first on adjudication quality, not on matching that
provider set exactly. First-party collection is implemented, but provider
parity is a shared-infrastructure concern, not a repo-local requirement.

### 2. Current repo contracts are not Tyler's exact enums

Tyler V1 uses one claim/dispute taxonomy. The current repo uses another:

- current `ClaimStatus`: `initial`, `supported`, `revised`, `refuted`,
  `inconclusive`
- current dispute types/routes are repo-local contracts, not Tyler's exact
  enum surface

Do not rename current contracts just to mimic Tyler's vocabulary unless the
change buys clearer behavior, better validation, or better benchmark results.

### 3. Cheap-model stabilization came before frontier-model parity

Tyler V1 is written around frontier-model role assignments.

The current repo intentionally stabilized the method on cheaper development
models before revisiting production/frontier configuration.

### 4. The current report contract is benchmarked, not schema-matched

The report/output surface does not exactly mirror Tyler's 3-tier V1 contract.
That is acceptable as long as grounding, dispute visibility, and benchmark
quality stay strong.

## Boundary Decisions

These decisions are locked unless a new plan changes them:

### 1. Provider adapters belong in shared infra

Do not add Tavily or Exa API clients directly in `grounded-research`.

If provider parity work is needed:

- `open_web_retrieval` owns search/fetch/extract provider adapters
- `grounded-research` consumes those adapters

Tyler-specific provider notes that should carry into shared infra:

- Exa semantic queries that rely on `systemPrompt` must use `type="deep"`
- provider failures and fallbacks should be visible through shared
  observability, not bespoke project logging

### 2. The `research_v3` upstream path is real

The `research_v3` -> `EvidenceBundle` -> `grounded-research --fixture` path is
supported and proven. Do not treat imported bundles as theoretical or
deprecated.

### 3. Gemini structured-output behavior is a shared-infra concern

Tyler's note about Gemini quality degrading under strict structured-output mode
is important, but it is not a `grounded-research`-only issue.

It belongs in:

- `llm_client` runtime/documentation
- `prompt_eval` comparison work

`grounded-research` should consume the result of that shared evaluation rather
than invent its own one-off execution policy.

## Future-Alignment Candidates

These are still legitimate future candidates, but they are not current repo
bugs:

1. Tavily + Exa provider parity through `open_web_retrieval`
2. Gemini JSON-Schema vs prompt-guided JSON comparison in `llm_client` /
   `prompt_eval`
3. Frontier-model production profile after cheap-model stabilization
4. Optional terminology parity if the current repo contracts are ever revised
   for clarity or benchmark gain

## What Not To Do

- Do not treat Tyler's V1 package as a literal bug list for this repo
- Do not re-open closed Tyler-alignment waves without a new benchmark or
  contract reason
- Do not move shared-infrastructure work back into this repo
