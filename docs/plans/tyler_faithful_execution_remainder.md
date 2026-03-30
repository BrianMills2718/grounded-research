# Tyler Faithful Execution Remainder

**Status:** Active
**Type:** remainder plan
**Priority:** High

## Goal

Define the smallest remaining work required to say, precisely and defensibly,
that `grounded-research` has faithfully executed Tyler's V1 plan.

This plan exists because repo-local runtime cutover is already complete, but a
few Tyler-required gaps remain:

- repo-local prompt literalness is now closed, with one documented Tyler
  Stage 2 schema/prompt ambiguity
- frozen eval evidence now covers two matched Tyler-vs-legacy cases, but it is
  still narrow directional evidence rather than broad proof
- Tyler-specified provider/model parity still depends on shared infrastructure

## Non-Goals

This plan does not reopen:

- deleted legacy runtime paths
- compatibility adapters in `main`
- new local provider clients
- broad repo-local cleanup waves without benchmark evidence

## Pre-Made Decisions

1. Tyler-literal remains the canonical runtime target in this repo.
2. Archived calibrated legacy remains eval-only; it does not return as a live
   runtime mode.
3. Prompt literalness is the default goal. Deviations are acceptable only when:
   - the Tyler spec is ambiguous, or
   - a concrete shared-infra/provider constraint forces the deviation.
4. Provider parity belongs in `open_web_retrieval`, not in this repo.
5. Model/runtime behavior studies belong in `llm_client` and `prompt_eval`, not
   in this repo.
6. Repo-local work closes before shared-infra work only where the boundary is
   clean and local.

## Success Criteria

This remainder plan is complete only if:

1. repo-local docs say exactly what is still local work vs shared-infra work,
2. repo-local prompt literalness is closed by a line-by-line audit and patch,
   with any remaining conflict documented as an explicit Tyler-internal
   ambiguity,
3. the frozen Tyler-vs-legacy comparison set is no longer a single-case story,
4. remaining provider/model parity gaps are explicitly named as external
   dependencies rather than implied local TODOs.

## Phases

### Phase 1: Close Repo-Local Prompt Literalness

**Status:** Completed

Scope:

- `prompts/tyler_v1_decompose.yaml`
- `prompts/tyler_v1_query_diversification.yaml`
- `prompts/tyler_v1_extract_findings.yaml`
- deterministic Stage 5 query generation in `src/grounded_research/verify.py`
- the stage call sites that invoke them

Deliverables:

- line-by-line Tyler prompt fidelity audit for Stage 1, 2, and 5
- prompt patches where the repo is still locally divergent
- explicit justified-deviation notes where literalness cannot be closed locally

Pass if:

- each of the remaining uncertain prompt surfaces is classified as:
  - literal
  - justified deviation
  - blocked by shared infra

Failure modes:

- audit only restates vague similarity without line-level findings
- a real local deviation is left undocumented
- provider/model constraints are misclassified as local prompt defects

Execution surface:

- `docs/plans/tyler_prompt_literalness_wave1.md`
- `docs/notebooks/31_tyler_prompt_literalness_wave1.ipynb`

### Phase 2: Expand Frozen Eval Coverage

**Status:** Completed

Scope:

- saved Tyler-literal benchmark outputs
- archived calibrated-legacy benchmark outputs
- `prompt_eval` frozen comparison path

Deliverables:

- at least one additional saved Tyler-vs-legacy comparison case beyond the
  tracked UBI pair
- updated result summary that says whether the current Tyler-literal default
  still holds across the expanded frozen set

Pass if:

- the comparison set is no longer effectively one case
- the result is recorded with explicit limits

Failure modes:

- cases are not actually matched
- outputs are too heterogeneous to support a real paired comparison

### Phase 3: Lock Shared-Infra Parity Boundaries

**Status:** Completed

Scope:

- Tavily/Exa provider parity
- Tyler frontier model-role parity
- Gemini structured-output behavior

Deliverables:

- explicit references to the owning shared-infra plan/doc surfaces
- no remaining ambiguous “future alignment” language in `grounded-research`

Pass if:

- every remaining non-local Tyler gap has a named owner:
  - `open_web_retrieval`
  - `llm_client`
  - `prompt_eval`

Failure modes:

- repo docs still imply shared-infra work belongs here
- “faithful Tyler execution” is declared without naming these external blockers

## Current Known Gaps

Repo-local:

1. none

Shared infra:

1. Exa parity in `open_web_retrieval` (Tavily parity and app consumption are now shipped)
2. frontier-model role parity in production config / availability
3. Gemini schema-mode quality study in `llm_client` / `prompt_eval`

Evaluation:

1. frozen Tyler-vs-legacy comparison now has two-case directional coverage only

## Acceptance Rule

Faithful Tyler execution can be claimed only if:

- repo-local runtime and export contracts are Tyler-native,
- remaining prompt-literalness uncertainty is closed or justified explicitly,
- frozen eval evidence is broader than a single shared case,
- all remaining non-local differences are explicitly assigned to shared infra.

Until then, the accurate claim is:

- repo-local Tyler runtime parity is complete,
- faithful Tyler execution is still in progress.

## Canonical Status Surface

For the strict `required / extension / blocked` checklist, use:

- `docs/TYLER_EXECUTION_STATUS.md`
