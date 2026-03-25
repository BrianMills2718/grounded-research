# Plan: V1 Design Gap Closure

**Source:** Tyler's review of current codebase vs original V1 design
**Status:** Planned
**Priority:** High

## Gaps (ordered by impact)

### 1. Claim Extraction Precision
**Gap:** Analysts produce "pilot programs show minimal effects" not "The Finnish
experiment (N=2,000, 2017-2018) found no significant employment difference."
**Root cause:** Prompt instruction exists but isn't biting. Schema `Field(description)`
for RawClaim.statement says to include specifics but LLMs still abstract.
**Fix:** Two-part:
- (a) Add a claim validation pass after extraction: check each claim for
  quantitative specifics (regex for N=, %, study names). Flag abstract claims.
- (b) If abstract claims detected, re-prompt the analyst with the specific
  evidence items and ask for revision with concrete details.
**Where:** New function in `canonicalize.py`, new prompt `prompts/validate_claims.yaml`
**Acceptance:** ≥ 50% of claims contain named studies or specific numbers

### 2. Add Claude to Analyst Pool
**Gap:** No Anthropic models in the analyst pool. Missing a major reasoning architecture.
**Fix:** Add `openrouter/anthropic/claude-sonnet-4-6` to analyst_models config.
Expand from 3 to 4 analysts (or replace DeepSeek).
**Where:** `config/config.yaml` analyst_models
**Decision needed:** 3 analysts (replace DeepSeek) or 4 analysts (add Claude)?
4 is better for disagreement diversity but costs more.
**Acceptance:** Claude analyst produces claims with different analytical character

### 3. Protocol-Level Anti-Conformity
**Gap:** ADR-0004 checks that non-inconclusive verdicts have new_evidence_ids,
but doesn't validate that the evidence actually supports the position change.
LLM could cite irrelevant evidence.
**Fix:** After arbitration, validate: for each claim_update, check that at least
one new_evidence_id's content is semantically relevant to the claim being updated.
Simple LLM call: "Does this evidence [text] support changing this claim [text]
from [old status] to [new status]? Yes/No with reasoning."
**Where:** `verify.py` after `arbitrate_dispute()`, new prompt
**Acceptance:** No verdict changes without validated evidence relevance

### 4. Anonymization Enforcement in Code
**Gap:** Alpha/Beta/Gamma labels exist but no string replacement strips model
self-identification from outputs. "As an OpenAI model..." would leak through.
**Fix:** After each analyst run, regex scan for model identity phrases
("As a [model]", "OpenAI", "GPT", "Claude", "Gemini", "DeepSeek", "as an AI")
in claims, summary, and recommendations. Strip or warn.
**Where:** `engine.py` after analyst runs (extend existing evidence leakage check)
**Acceptance:** No model identity strings in analyst outputs passed to downstream

### 5. Baseline Discipline at Pipeline Level
**Gap:** No in-pipeline check that the result beats single-shot. Comparison
scripts exist but aren't part of the pipeline.
**Fix:** Optional post-pipeline baseline check: after report generation, run
a single-shot synthesis on the same evidence bundle and compare via judge.
Flag if pipeline score ≤ single-shot score.
**Where:** `engine.py` as optional post-pipeline step, config flag `run_baseline_check: false`
**Decision needed:** Always run (doubles cost) or opt-in flag?
**Acceptance:** Pipeline warns if it doesn't beat single-shot on a given run

### 6. Dedup Reliability
**Gap:** Dedup returns 0 groups ~30% of runs via OpenRouter/Gemini. Fallback
works but means no dedup happened.
**Fix:**
- (a) Switch dedup model to gpt-5-nano (already done in config, but verify)
- (b) Add retry: if 0 groups returned, retry once with a simplified prompt
- (c) If still 0, fall back to 1:1 (current behavior)
**Where:** `canonicalize.py` deduplicate_claims()
**Acceptance:** 0-groups rate < 5%

## Implementation Order

1. #2 Claude analyst (config change, 5 min)
2. #4 Anonymization (regex scan, 15 min)
3. #6 Dedup retry (add retry logic, 15 min)
4. #1 Claim precision validation (new function + prompt, 30 min)
5. #3 Anti-conformity validation (new function + prompt, 30 min)
6. #5 Baseline discipline (optional post-pipeline, 45 min)
