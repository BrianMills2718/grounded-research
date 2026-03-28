# Tyler Stage 3 Model-Role Recovery

**Status:** In Progress
**Parent plan:** `docs/plans/tyler_literal_prompt_quality_recovery.md`
**Purpose:** Recover Tyler-native Stage 3 quality by aligning the active
analyst role/model assignment to the closest available Tyler mapping and
removing the currently observed DeepSeek structured-output failure mode from the
primary analyst path.

## Why This Wave Exists

The tracked Tyler-native UBI rerun at
`output/tyler_literal_parity_ubi_reanchor_v6/` improved materially after the
Stage 6 synthesis prompt repair:

- `25` Stage 4 claims
- `5` disputes
- `8` cited final claims

But it still loses to both saved anchors:

- `output/ubi_perplexity/perplexity_report.md`
- `output/ubi_dense_dedup_eval/report.md`

And the live run exposed a concrete Stage 3 problem:

- the DeepSeek analyst path produced malformed `AnalysisObject` attempts before
  the pipeline recovered
- the final analyst density remained uneven:
  - Alpha: `13` claims
  - Beta: `5` claims
  - Gamma: `3` claims

This is now the clearest repo-local quality bottleneck left after the Stage 6
repair and export grounding fix.

## Scope

This wave covers repo-local Stage 3 configuration and runtime behavior only:

1. make the primary Stage 3 analyst order match Tyler's intended reasoning
   frames as closely as the locally available model registry allows
2. remove `deepseek-chat` from the primary analyst path because it is failing
   the live schema contract on the tracked benchmark
3. rerun the same Tyler-native UBI benchmark and compare it against the same
   saved anchors

This wave does **not**:

- add new shared-infra provider integrations
- claim literal Claude Opus parity if the model is not locally available in the
  shared model registry
- reopen Stage 4-6 contracts

## Pre-Made Decisions

1. Tyler's exact Stage 3 model stack is not locally available in the current
   shared registry, so this wave uses the closest available mapping and records
   the remaining gap explicitly.
2. The primary analyst order must match Tyler's frame order:
   - A = step-back abstraction
   - B = structured decomposition
   - C = verification-first
3. `deepseek-chat` is removed from the primary analyst trio because the tracked
   live benchmark already proved it is not reliably satisfying the Stage 3
   structured schema.
4. The closest available primary trio is:
   - A = `openrouter/openai/gpt-5.4-mini`
   - B = `gemini/gemini-2.5-flash`
   - C = `openrouter/openai/gpt-5.4-nano`
5. If this closest-available role recovery still loses badly, the remaining gap
   is no longer "Stage 3 config ambiguity." It becomes either:
   - literal frontier-model unavailability, or
   - a deeper prompt/shared-infra issue.

## Acceptance Criteria

This wave passes only if:

1. the primary Stage 3 config reflects the pre-made closest-available Tyler
   role order
2. deterministic tests covering Tyler Stage 3 runtime still pass
3. the rerun completes with:
   - no export grounding warnings
   - no analyst below `5` claims
4. the rerun is no worse than v6 on:
   - Stage 4 claim count
   - final cited-claim count
5. any remaining gap to Tyler's exact model-role spec is recorded explicitly as
   a local model-availability concern, not buried

## Execution Order

### Slice 1: Planning + Config Cutover

- add notebook planning artifact
- update `config/config.yaml`
- if needed, add one small regression test for Stage 3 runtime defaults

### Slice 2: Deterministic Verification

- run targeted Stage 3/runtime suites
- run export/prompt/phase-boundary suites to ensure no regression in later
  Tyler-native stages

### Slice 3: Tracked UBI Gate

- rerun:
  - `output/tyler_literal_parity_ubi_reanchor_v7/`
- compare against:
  - `output/ubi_perplexity/perplexity_report.md`
  - `output/ubi_dense_dedup_eval/report.md`

### Slice 4: Closure

- update:
  - `docs/plans/tyler_literal_prompt_quality_recovery.md`
  - `docs/TYLER_LITERAL_PROMPT_FIDELITY_AUDIT.md`
  - `docs/TYLER_LITERAL_PARITY_AUDIT.md`
  - `docs/PLAN.md`
  - `docs/plans/CLAUDE.md`

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| closest-available role recovery still produces sparse analysts | one or more analysts still return <5 claims | treat Stage 3 prompt content, not just model-role assignment, as the next local slice |
| removing DeepSeek hurts diversity too much | outputs become more homogeneous and usefulness drops | record the tradeoff explicitly; schema reliability still takes precedence over fake diversity |
| benchmark improves mechanically but still loses | more claims/disputes/citations but weaker decision framing | keep Stage 3 closed and return to Stage 6 usefulness rather than reopening the same config question |
| exact Tyler model-role parity is requested literally | current shared registry still lacks Claude Opus 4.6 | record as an explicit external/model-availability concern rather than pretending local config solved it |
