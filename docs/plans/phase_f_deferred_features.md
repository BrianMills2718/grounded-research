# Phase F: Implement Deferred/Cut Features

**Status:** Planned
**Scorecard items:** #3, #8, #9, #10, #12, #30, #38

## Group 1: Decomposition Validation (#8, #9, #10, #12)

One LLM call after decomposition, before search. Validates the decomposition
and optionally triggers one retry.

**Input:** `QuestionDecomposition` + original question
**Output:** `DecompositionValidation` (coverage_ok, bias_flags, granularity_issues, verdict)

**Schema:**
```python
class DecompositionValidation(BaseModel):
    coverage_ok: bool  # Do sub-questions collectively cover the full question?
    coverage_gaps: list[str]  # What aspects of the question are missed?
    bias_flags: list[str]  # Sub-questions with leading/directional framing
    granularity_issues: list[str]  # Sub-questions that are too broad, narrow, or redundant
    verdict: Literal["proceed", "revise"]  # proceed = good enough, revise = re-decompose
    revision_guidance: str  # If revise, what to fix (fed back to decompose prompt)
```

**Flow:**
1. After `decompose_question()`, call `validate_decomposition()`
2. If verdict = "revise", re-run `decompose_question()` with revision_guidance appended to prompt
3. Max 1 retry (no infinite loops)
4. If retry also gets "revise", proceed anyway with warning

**Pre-made decisions:**
- Model: same as decomposition (`gemini/gemini-2.5-flash`)
- New prompt: `prompts/validate_decomposition.yaml`
- New file: `src/grounded_research/decompose.py` (extend existing)
- Config: no new keys needed (reuses decomposition model)
- Wired in: `engine.py` run_pipeline_from_question, after decompose, before collect

## Group 2: Small Features (#3, #30, #38)

### #3: Ambiguous Term Disambiguation

Add `ambiguous_terms` field to `QuestionDecomposition`. The decomposition
LLM already has the question context — just add a schema field and prompt
instruction to identify terms that could be interpreted multiple ways and
state which interpretation is used.

**Schema addition:**
```python
class AmbiguousTerm(BaseModel):
    term: str  # The ambiguous term
    chosen_interpretation: str  # How it's interpreted in this decomposition
    alternative: str  # What it could also mean
```

**Changes:**
- Add `AmbiguousTerm` to models.py
- Add `ambiguous_terms: list[AmbiguousTerm]` to `QuestionDecomposition`
- Update `prompts/decompose.yaml` to ask for ambiguous terms
- Pass to analyst prompt for context

### #30: Evidence-Label Leakage Check

Code-only check (no LLM). After analyst runs, verify analyst outputs don't
contain source URLs that could identify which source provided which evidence
(breaking the blindness principle).

**Logic:** Scan each `AnalystRun.claims[].statement` and `AnalystRun.summary`
for URL patterns. If found, warn.

**Changes:**
- Add `_check_evidence_leakage()` in engine.py after analysts
- Emits PipelineWarning if URLs found in analyst text

### #38: Shuffle Analyst Positions in Arbitration

Before arbitration, shuffle the order of claims in dispute context to prevent
primacy bias (first-listed claim gets more weight).

**Changes:**
- In `verify.py` `arbitrate_dispute()`, shuffle `dispute.claim_ids` order
  before constructing arbitration prompt
- Use `random.shuffle` with fixed seed per dispute (reproducible)

## Implementation Sequence

1. Add `AmbiguousTerm` to models.py, add field to `QuestionDecomposition` (#3)
2. Update `prompts/decompose.yaml` for ambiguous terms (#3)
3. Add `DecompositionValidation` schema to models.py (#8-10, #12)
4. Write `prompts/validate_decomposition.yaml` (#8-10, #12)
5. Add `validate_decomposition()` to decompose.py (#8-10, #12)
6. Wire validation + retry into engine.py (#12)
7. Add evidence-label leakage check in engine.py (#30)
8. Add position shuffling in verify.py (#38)
9. Update analyst prompt to show ambiguous terms (#3)
10. Run tests

## Acceptance Criteria

- #3: Decomposition output includes ambiguous terms when relevant
- #8: Validation catches a missing coverage dimension
- #9: Validation flags a biased sub-question framing
- #10: Validation flags overly broad or redundant sub-questions
- #12: "revise" verdict triggers re-decomposition that produces better output
- #30: URL in analyst claim text triggers warning
- #38: Claim order in arbitration prompt is shuffled per dispute
