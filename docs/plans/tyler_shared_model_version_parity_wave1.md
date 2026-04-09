# Tyler Shared Model Version Parity Wave 1

**Status:** Active
**Type:** shared-parity plan
**Priority:** Medium
**Parent plan:** `docs/plans/tyler_faithful_execution_remainder.md`

## Goal

Resolve the remaining exact Tyler model-version parity row by determining
whether the shared stack can expose and validate Tyler's named Gemini 3.1 Pro
surface, or whether the current Gemini 2.5 Pro substitution must remain a
documented constraint.

## Scope

In scope:

- shared `llm_client` model registry and model-identity surfaces
- exact Gemini 3 Pro / 3.1 Pro provider IDs available to the shared stack
- whether `grounded-research` can switch cleanly from Gemini 2.5 Pro to the
  Tyler-named Gemini 3.x Pro surface for decomposition and structured analyst
  work

Out of scope:

- changing unrelated model-routing policy
- broad benchmark expansion
- speculative local substitutions inside `grounded-research`

## Pre-Made Decisions

1. This is a shared stack question, not a local app workaround question.
2. The row closes only if one of these is proven:
   - exact Gemini 3.x Pro parity is wired and validated through the shared
     stack, or
   - exact parity is still unavailable/impractical and remains explicitly
     documented as a shared constraint.
3. `grounded-research` will not claim exact Tyler model-version parity until
   the shared registry/config surface supports it and a targeted validation run
   succeeds.

## Review Questions

1. What exact provider/model identifier should stand in for Tyler's Gemini 3.1
   Pro request in the current ecosystem? Current best candidate:
   `openrouter/google/gemini-3.1-pro-preview`
2. Does `llm_client` currently expose that identifier in its shared registry or
   routing surfaces?
3. If not, is the blocker:
   - missing registry entry,
   - missing provider support,
   - structured-output confidence gap,
   - or deliberate policy choice?
4. What is the minimal validation needed before `grounded-research` can adopt
   it?

## Success Criteria

This wave passes only if:

1. `S3-MODEL-VERSION-001` is narrowed to a concrete shared action or a concrete
   documented constraint,
2. the repo no longer uses vague wording like “closest available” without
   naming the exact missing shared surface,
3. the next action is explicit enough to execute in `llm_client` without
   reinterpretation.

## Verification

Minimum evidence:

1. current `grounded-research` config reviewed
2. current `llm_client` model registry reviewed
3. external provider/model existence checked against official or provider
   model pages
4. resulting status reflected in the ledger and status docs

## Todo List

- [x] review current app config
- [x] review current shared registry surface
- [x] confirm external model existence
- [x] decide whether the next step is shared registry wiring or documented hold

## Current Finding

Current state is already narrower than before:

- Tyler names Gemini 3.1 Pro
- `grounded-research` still uses `openrouter/google/gemini-2.5-pro`
- OpenRouter currently exposes `google/gemini-3.1-pro-preview`
- `llm_client` shared default model registry does not yet expose a Gemini 3 Pro
  / 3.1 Pro entry

So the next step is no longer “investigate generic availability.”
It is:

- decide whether to wire the exact Gemini 3.x Pro surface into the shared
  registry and validate it, or explicitly hold the substitution as a shared
  constraint

## Progress Note (2026-04-09)

The first shared follow-through slice is now active:

- `llm_client` branch: `gemini31-model-parity`
- PR: `#28`
- shared result:
  - `openrouter/google/gemini-3.1-pro-preview` added to the packaged registry
  - Tyler-like structured-output study passed `5/5` via `native_schema`

So the next app-local step is now explicit:

- merge `llm_client` PR #28
- then switch `grounded-research` config from
  `openrouter/google/gemini-2.5-pro` to
  `openrouter/google/gemini-3.1-pro-preview`
- then rerun the targeted Tyler validation lane
