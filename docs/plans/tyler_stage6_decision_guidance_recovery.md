# Tyler Stage 6 Decision-Guidance Recovery

**Status:** In Progress
**Parent plan:** `docs/plans/tyler_literal_prompt_quality_recovery.md`
**Purpose:** Recover decision usefulness on the Tyler-native path by repairing
underfilled Stage 6 synthesis fields, especially tradeoffs, alternatives, and
disagreement coverage.

## Why This Wave Exists

The tracked Tyler-native UBI rerun at
`output/tyler_literal_parity_ubi_reanchor_v7_retry1/` now:

- beats cached Perplexity on decision usefulness
- completes with `0` grounding warnings
- improves Stage 3 and Stage 4 density materially

But it still loses to the saved dense-dedup anchor because the final report is
less prescriptive and less fully packaged for policy decisions.

Most obvious symptom:

- the `Decision-Relevant Tradeoffs` section is empty in the rendered report

That makes the next local bottleneck a Stage 6 underfill problem, not another
Stage 3 or Stage 4 ambiguity.

## Scope

This wave covers:

1. stronger Stage 6 prompt pressure on decision tradeoffs, alternatives, and
   unresolved-dispute coverage
2. a small Stage 6 repair loop when critical synthesis fields are underfilled
3. rerun of the same tracked UBI fixture benchmark

This wave does **not**:

- reopen Stage 1-5 contracts
- change retrieval or arbitration policy
- claim shared-infra provider/model parity

## Pre-Made Decisions

1. Treat empty `decision_relevant_tradeoffs` as a local synthesis failure, not
   as an acceptable output variant.
2. If unresolved disputes exist, the disagreement map must mention them.
3. If the evidence supports a default recommendation but plausible alternatives
   survive, at least one preserved alternative must be surfaced.
4. Use a repair loop before changing broader synthesis architecture.

## Acceptance Criteria

This wave passes only if the rerun:

1. completes with `0` grounding warnings
2. has at least:
   - `1` decision tradeoff
   - `1` preserved alternative when viable alternatives survive
3. is no worse than v7 on:
   - Stage 4 claim count
   - cited-claim count
4. improves decision usefulness enough to tie or beat the dense-dedup anchor,
   or leaves a precise, evidence-backed residual gap
