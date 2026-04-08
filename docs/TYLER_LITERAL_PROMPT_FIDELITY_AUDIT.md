# Tyler Literal Prompt Fidelity Audit

**Status:** Updated after prompt-literalness wave closure
**Purpose:** Identify whether the active Tyler-native prompt files are truly
literal Tyler prompt implementations or still adapted simplifications that
likely explain the current benchmark regression.

**Audit note (2026-04-08):** This document predates the clause-by-clause gap
ledger. Where it conflicts with `docs/TYLER_SPEC_GAP_LEDGER.md`, trust the
ledger. In particular, Stage 2 query diversification should no longer be read
as conclusively literal.

## Executive Verdict

The live Tyler-native prompt package is **not fully closed by this document
alone**. Earlier prompt-literalness waves landed, but the April 2026
clause-by-clause audit found additional prompt/orchestrator divergences that
are now tracked in the canonical gap ledger. This file should be read as
historical prompt-focused context, not as the final authority on open gaps.

Current state:

- runtime is Tyler-native at the schema/artifact level
- active prompt files exist for Stage 1-6
- Stage 1, Stage 2, and Stage 5 have now been audited line by line
- Stage 5 lives only in the deterministic builder in `verify.py`; the dead
  `prompts/verification_queries.yaml` surface has been deleted

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
| Stage 1 decomposition | `prompts/tyler_v1_decompose.yaml` | Literal | shared output protocol restored to Tyler wording |
| Stage 2 query diversification | `prompts/tyler_v1_query_diversification.yaml` | Literal | prompt already matched Tyler closely; wording confirmed line by line |
| Stage 2 finding extraction | `prompts/tyler_v1_extract_findings.yaml` | Literal except one justified Tyler-internal ambiguity | shared protocol restored; reasoning-field line omitted because Tyler's own `Finding` schema has no reasoning field |
| Stage 3 analyst | `prompts/tyler_v1_analyst.yaml` | Literal enough locally; model-role recovery completed | v7 recovered analyst density to `9/20/6` and v8 stayed healthy at `8/17/7` |
| Stage 4 claim extraction | `prompts/tyler_v1_stage4.yaml` | Literal enough locally | later recovery runs reached `28` and then `38` Tyler claims |
| Stage 5 verification queries | `src/grounded_research/verify.py::_build_tyler_verification_queries` | Literal behavior | neutral, weaker-position, authoritative, and optional dated query roles are now explicit and tested |
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

Prompt-focused status can be classified honestly as:

1. Tyler-native prompt/runtime quality now beats cached Perplexity on the
   tracked UBI benchmark
2. the remaining gap to the dense-dedup anchor is small and evidence-backed,
   not an unclassified local defect
3. one Stage 2 prompt/schema conflict remains explicitly documented as a Tyler
   internal ambiguity, not a hidden local TODO
4. exact frontier-model parity and provider assumptions remain shared-infra /
   model-availability concerns, not hidden local TODOs

The remaining faithful-Tyler execution work is tracked in:

- `docs/plans/tyler_faithful_execution_remainder.md`
