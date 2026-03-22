# ADR-0005: Cross-Family Models and Distinct Frames Required

## Status

Accepted

## Context

Phase -1 thesis validation initially ran 3 analysts using the same model
(`gemini/gemini-2.5-flash-lite`) with the same frame (`general`). This measured
stochastic variation in identical runs — temperature noise — not genuine
analytical disagreement.

The entire value proposition of grounded-research rests on meaningful
disagreement between analysts. If all analysts are the same model with the same
instructions, disagreement is random noise indistinguishable from running the
same prompt 3 times and looking for differences.

A strategic review (2026-03-22) identified this as a circular validation:
the thesis was "proven" under conditions that could not falsify it.

## Decision

1. **Analyst models MUST come from different model families.** The default
   config uses Gemini, OpenAI, and DeepSeek. Same-family runs are acceptable
   only for cost/debugging, never for thesis validation.

2. **Analyst frames MUST be distinct.** The three frames are:
   - `verification_first` — prioritizes falsification and contradiction detection
   - `structured_decomposition` — breaks questions into orthogonal sub-questions
   - `step_back_abstraction` — reasons from broader principles to specifics

3. **The old `phase_minus1_models` config key is replaced by `analyst_models`.**

## Consequences

- Re-ran Phase -1 on a factual question (PFAS health risks) with cross-family
  models and distinct frames. Result: 5 disputes (1 decision-critical factual
  conflict about EPA regulatory timeline), resolved with 6 pieces of fresh
  evidence. Analysts produced meaningfully different claim counts and different
  analytical perspectives.

- This is a necessary but not sufficient condition for thesis validation. A
  controlled comparison against single-shot synthesis (via `prompt_eval`) is
  still required to prove the pipeline adds value over simpler approaches.

- Cost per pipeline run increases slightly (~$1-2 vs ~$0.50 with flash-lite × 3)
  but remains well within the $5 budget.
