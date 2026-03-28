# Tyler Literal Prompt Quality Recovery

**Status:** Completed
**Parent plan:** `docs/plans/tyler_literal_parity_refactor.md`
**Purpose:** Recover benchmark usefulness on the now-stable Tyler-native
runtime by auditing and tightening literal prompt fidelity and stage-level
quality where the contract migration alone proved insufficient.

## Why This Wave Existed

The Tyler-native runtime now works end-to-end, but the tracked UBI re-anchor
still regressed badly in decision usefulness:

- `output/tyler_literal_parity_ubi_reanchor_v5/`
- only `12` Stage 4 claims and `2` cited final claims
- loses to both:
  - `output/ubi_perplexity/perplexity_report.md`
  - `output/ubi_dense_dedup_eval/report.md`

This means contract literalism alone is not enough. The next gap is quality:

1. some live Tyler prompt files may still be adapted rather than literal
2. some Tyler-native stages may be under-performing because of prompt shape,
   model assignment, or over-compression of evidence into later stages

## Scope

This wave covers repo-local work only:

1. stage-by-stage audit of the active Tyler prompt files against
   `tyler_response_20260326/4. V1_PROMPTS (1).md`
2. diagnosis of which Tyler-native stages are quality bottlenecks on the tracked
   UBI benchmark
3. prompt/runtime fixes for those local bottlenecks
4. rerun of the same tracked benchmark gate

It also records one explicit local concern that may need a deliberate decision:

- current stage-model assignments still differ materially from Tyler's preferred
  frontier-model stack, even though the runtime contracts are Tyler-native

This wave does **not** pull shared-infra work back into the repo:

- Tavily/Exa parity stays in `open_web_retrieval`
- provider behavior studies stay in `llm_client` / `prompt_eval`

## Pre-Made Decisions

1. Treat the current benchmark regression as a local quality problem until a
   stage-level audit proves otherwise.
2. Audit prompt literalness before changing any more stage splitting or schema
   contracts.
3. Use the same tracked UBI fixture for all comparisons in this wave.
4. Evaluate the weakest stages first:
   - Stage 3 analyst outputs
   - Stage 4 claim extraction density
   - Stage 6 synthesis usefulness
5. Do not reopen Stage 1-6 contract migration unless the audit finds a
   contract-level mismatch disguised as a prompt issue.
6. Do not silently treat cheap dev-model assignments as "close enough" to
   Tyler's specified quality bar; either justify them with benchmark evidence or
   record model-parity as an open concern.

## Acceptance Criteria

This wave is complete only if:

1. every active Tyler prompt file is classified as:
   - literal
   - adapted but acceptable
   - adapted and must change
2. the tracked UBI rerun improves materially over
   `output/tyler_literal_parity_ubi_reanchor_v5/`
3. the rerun either:
   - preserves usefulness against the dense-dedup anchor, or
   - records a precise, evidence-backed reason why literal Tyler prompt parity
     still loses
4. any unresolved gap is tagged as repo-local or shared-infra, not left
   ambiguous

## Outcome

This wave completed in two gate-time sub-slices:

1. Stage 3 role recovery:
   - `docs/plans/tyler_stage3_model_role_recovery.md`
   - closest-available Tyler role ordering
   - DeepSeek removed from the primary analyst path
2. Stage 6 decision-guidance recovery:
   - `docs/plans/tyler_stage6_decision_guidance_recovery.md`
   - underfilled decision-field repair loop
   - stronger Stage 6 prompt pressure for tradeoffs/alternatives/disagreement coverage

Final tracked result:

- `output/tyler_literal_parity_ubi_reanchor_v8/`

Compared with the original v5 trigger:

- Stage 3 improved from `10/6/3` claims to `8/17/7`
- Stage 4 improved from `12` claims and `1` dispute to `38` claims and `3` disputes
- Stage 6 improved from `2` cited claims to `6`
- export grounding warnings dropped to `0`

Outcome classification:

- repo-local Tyler-native quality recovery is materially successful
- the Tyler-native path now beats cached Perplexity on the tracked UBI question
- it still trails the saved dense-dedup anchor slightly, for an explicit reason:
  the dense-dedup path still packages broader contextual alternatives and
  uncertainty framing a bit better than the Tyler-native path

That remaining difference is now evidence-backed rather than ambiguous.

## Execution Order

### Slice 1: Prompt Fidelity Audit

- compare active Tyler prompt files against Tyler's prompt spec
- produce one row per stage:
  - Stage 1 decomposition
  - Stage 2 query diversification / finding extraction
  - Stage 3 analyst
  - Stage 4 claim extraction
  - Stage 5 arbitration
  - Stage 6 synthesis

Pass if:

- every stage has a clear literal/adapted classification
- the largest prompt-level divergences are explicitly named

### Slice 2: Stage Weakness Diagnosis

- inspect `output/tyler_literal_parity_ubi_reanchor_v5/trace.json`
- identify which stage first becomes too thin for decision-useful output
- use concrete metrics:
  - Stage 2 source counts
  - Stage 3 claim counts per analyst
  - Stage 4 canonical claims/disputes
  - Stage 6 cited claims / disagreement coverage / alternatives coverage

Pass if:

- one primary weakness and at most two secondary weaknesses are identified

### Slice 3: Local Quality Fixes

- fix the weakest Tyler-native stages without reopening already-stable contract
  work
- likely surfaces:
  - `prompts/tyler_v1_analyst.yaml`
  - `prompts/tyler_v1_stage4.yaml`
  - `prompts/tyler_v1_synthesis.yaml`
  - `config/config.yaml` if the audit shows that current stage-model
    assignments are themselves a local parity blocker
  - stage-local runtime wiring if the prompt audit proves a local assembly bug

Pass if:

- deterministic tests still pass
- the tracked UBI rerun shows materially stronger claim density and cited-claim
  coverage

### Slice 4: Benchmark Gate

- rerun the tracked UBI fixture benchmark on the repaired Tyler-native path
- compare against:
  - `output/ubi_perplexity/perplexity_report.md`
  - `output/ubi_dense_dedup_eval/report.md`

Pass if:

- usefulness is no worse than the dense-dedup anchor, or
- remaining loss is explicitly traced to a non-local shared-infra factor

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| literal prompt audit finds current prompts already literal | quality still regresses despite literal prompt text | treat model behavior or shared-infra evidence sourcing as the likely next boundary |
| Stage 3 remains too sparse | analysts produce too few claims even with rich Stage 2 inputs | tighten Stage 3 prompt fidelity first |
| Stage 4 over-compresses | Stage 3 has reasonable density but Stage 4 collapses too aggressively | tighten Stage 4 prompt fidelity and dispute-localization instructions |
| Stage 6 under-cites | upstream stages look reasonable but final report cites too few claims | tighten Stage 6 prompt fidelity and projection rules |
| prompt fidelity is fine but outputs remain weak | Tyler-native prompts are already literal enough, but cheap stage-model assignments still underperform | record model-parity as a local open concern and decide explicitly whether to pay for Tyler-like frontier assignments |
| benchmark still loses after local fixes | Tyler-native path remains worse than prior calibrated runtime | record that literal Tyler parity and benchmark optimum diverge, then stop pretending the gap is unclassified |
