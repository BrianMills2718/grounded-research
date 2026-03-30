# Tyler Literal Prompt Fidelity Audit

**Status:** Updated after Stage 3 and Stage 6 recovery
**Purpose:** Identify whether the active Tyler-native prompt files are truly
literal Tyler prompt implementations or still adapted simplifications that
likely explain the current benchmark regression.

## Executive Verdict

The live Tyler-native prompt package is **materially closer to literal and now
quality-recovered enough to beat cached Perplexity on the tracked UBI case**,
but it is still not identical to the prior benchmark-optimal dense-dedup path.

Current state:

- runtime is Tyler-native at the schema/artifact level
- active prompt files exist for Stage 1-6
- but at least some live prompt files are still compressed or adapted relative
  to `tyler_response_20260326/4. V1_PROMPTS (1).md`

This was the leading local explanation for why the Tyler-native UBI rerun at
`output/tyler_literal_parity_ubi_reanchor_v5/` was mechanically stable but
still weak in decision usefulness. The later v7/v8 recovery waves improved that
substantially.

One additional explicit concern remains local and should not be hidden inside
"prompt quality":

- current stage-model assignments still use cheaper dev models in places where
  Tyler's spec assumed stronger frontier models

## Stage Classification

| Stage | Active file | Initial classification | Why |
|---|---|---|---|
| Stage 1 decomposition | `prompts/tyler_v1_decompose.yaml` | Not re-audited line by line; no benchmark evidence of a local defect | desired literalness is still an assumption, but there is no current grounded-research-specific failure signal here |
| Stage 2 query diversification | `prompts/tyler_v1_query_diversification.yaml` | Not re-audited line by line; no benchmark evidence of a local defect | current uncertainty is explicit rather than hidden |
| Stage 2 finding extraction | `prompts/tyler_v1_extract_findings.yaml` | Not re-audited line by line; no benchmark evidence of a local defect | current uncertainty is explicit rather than hidden |
| Stage 3 analyst | `prompts/tyler_v1_analyst.yaml` | Literal enough locally; model-role recovery completed | v7 recovered analyst density to `9/20/6` and v8 stayed healthy at `8/17/7` |
| Stage 4 claim extraction | `prompts/tyler_v1_stage4.yaml` | Literal enough locally | later recovery runs reached `28` and then `38` Tyler claims |
| Stage 5 verification queries | `prompts/verification_queries.yaml` | Adapted, not literal | already known from Tyler parity audit; this remains a real divergence |
| Stage 5 arbitration | `prompts/tyler_v1_arbitration.yaml` | Not re-audited line by line; contract is Tyler-native and no current benchmark defect is isolated here | literalness uncertainty remains explicit |
| Stage 6 synthesis | `prompts/tyler_v1_synthesis.yaml` | Literal enough locally with repair loop | v8 produced `3` tradeoffs, `2` preserved alternatives, and `6` cited claims |

## Recovery Progression

Tracked anchors:

- `output/tyler_literal_parity_ubi_reanchor_v5/trace.json`
- `output/tyler_literal_parity_ubi_reanchor_v7_retry1/trace.json`
- `output/tyler_literal_parity_ubi_reanchor_v8/trace.json`

Recovered state:

- Stage 2 remained healthy throughout
- Stage 3 density recovered materially after role reassignment
- Stage 4 no longer collapses to a tiny ledger
- Stage 6 no longer underfills tradeoffs/alternatives silently

Residual weakness is now narrower: the Tyler-native path still packages a bit
less breadth/context than the saved dense-dedup anchor, even after the local
prompt-quality repairs.

## Current Conclusion

Repo-local prompt-quality recovery is complete enough to classify honestly:

1. Tyler-native prompt/runtime quality now beats cached Perplexity on the
   tracked UBI benchmark
2. the remaining gap to the dense-dedup anchor is small and evidence-backed,
   not an unclassified local defect
3. exact frontier-model parity and provider assumptions remain shared-infra /
   model-availability concerns, not hidden local TODOs

The remaining faithful-Tyler execution work is tracked in:

- `docs/plans/tyler_faithful_execution_remainder.md`
