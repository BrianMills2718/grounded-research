# Tyler V1 -> Current Repo Map

This note maps Tyler's V1 package in `tyler_response_20260326/` to the current
`grounded-research` repo.

Use it as a boundary document:

- Tyler's V1 package is a reference architecture and prompt/schema package.
- The current repo is now a Tyler-native adjudication-centered runtime with its
  own benchmark history and shared-infra boundaries.
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
- Tyler-native Stage 1-6 runtime artifacts are the live canonical contract
- prompt hardening, Claimify-style extraction, anti-conformity enforcement,
  anonymization scrubbing, and dense canonicalization hardening were all landed
  during the Tyler-alignment waves

## Remaining Divergences

These differences are deliberate, explicit, or still open:

### 1. Adjudication thesis over provider parity

Tyler's V1 locks Stage 2/5 around Tavily + Exa.

The current repo is judged first on adjudication quality, not on matching that
provider set exactly. First-party collection is implemented, but provider
parity is a shared-infrastructure concern, not a repo-local requirement.

### 2. Frontier-model parity is still not literal

Tyler V1 is written around stronger frontier-model role assignments than the
current shipped config can use reliably and locally.

### 3. Prompt literalness is not fully closed

The live runtime uses Tyler-stage prompt files, but Stage 1, Stage 2, and Stage
5 still have explicit prompt-literalness uncertainty. Stage 5 verification
query generation remains adapted rather than literal.

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
4. Frozen eval expansion beyond the single tracked UBI Tyler-vs-legacy case
5. Line-by-line closure of remaining prompt-literalness uncertainty

## What Not To Do

- Do not treat Tyler's V1 package as a literal bug list for this repo
- Do not re-open closed Tyler-alignment waves without a new benchmark or
  contract reason
- Do not move shared-infrastructure work back into this repo
