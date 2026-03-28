# Tyler Literal Prompt Fidelity Audit

**Status:** Initial audit complete
**Purpose:** Identify whether the active Tyler-native prompt files are truly
literal Tyler prompt implementations or still adapted simplifications that
likely explain the current benchmark regression.

## Executive Verdict

The live Tyler-native prompt package is **not yet safely claimable as fully
literal**.

Current state:

- runtime is Tyler-native at the schema/artifact level
- active prompt files exist for Stage 1-6
- but at least some live prompt files are still compressed or adapted relative
  to `tyler_response_20260326/4. V1_PROMPTS (1).md`

This is now the leading local explanation for why the Tyler-native UBI rerun at
`output/tyler_literal_parity_ubi_reanchor_v5/` was mechanically stable but
still weak in decision usefulness.

## Stage Classification

| Stage | Active file | Initial classification | Why |
|---|---|---|---|
| Stage 1 decomposition | `prompts/tyler_v1_decompose.yaml` | Needs audit | likely close, but not yet line-checked against Tyler source |
| Stage 2 query diversification | `prompts/tyler_v1_query_diversification.yaml` | Needs audit | likely close, but not yet line-checked |
| Stage 2 finding extraction | `prompts/tyler_v1_extract_findings.yaml` | Needs audit | likely close, but not yet line-checked |
| Stage 3 analyst | `prompts/tyler_v1_analyst.yaml` | Adapted and must audit closely | current live output is sparse (`10/6/3` claims) despite rich Stage 2 inputs |
| Stage 4 claim extraction | `prompts/tyler_v1_stage4.yaml` | Adapted and must audit closely | current live output compresses to `12` claims and `1` dispute on the tracked UBI rerun |
| Stage 5 verification queries | `prompts/verification_queries.yaml` | Adapted, not literal | already known from Tyler parity audit; this remains a real divergence |
| Stage 5 arbitration | `prompts/tyler_v1_arbitration.yaml` | Needs audit | contract is Tyler-native, but prompt literalness still needs explicit review |
| Stage 6 synthesis | `prompts/tyler_v1_synthesis.yaml` | Adapted and must audit closely | final report cites only `2` claims and under-delivers on alternatives/tradeoffs |

## Why Stage 3, 4, and 6 Are The First Targets

Tracked UBI rerun:

- `output/tyler_literal_parity_ubi_reanchor_v5/trace.json`

Key symptoms:

- Stage 2 is no longer empty:
  - source counts by sub-question: `15, 16, 15, 4, 11`
- Stage 3 remains relatively thin:
  - claim counts by analyst: `10, 6, 3`
- Stage 4 compresses aggressively:
  - `12` claims
  - `1` dispute
- Stage 6 is under-cited:
  - `2` cited claims

That makes Stage 3, Stage 4, and Stage 6 the highest-value prompt-fidelity
review surfaces.

## Immediate Next Step

Execute:

- `docs/plans/tyler_literal_prompt_quality_recovery.md`

Specifically:

1. line-check Stage 3, Stage 4, and Stage 6 against Tyler's prompt spec
2. identify missing or compressed instruction blocks
3. repair the prompt files
4. rerun the tracked UBI benchmark gate
