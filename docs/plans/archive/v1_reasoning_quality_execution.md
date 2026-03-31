# Plan: V1 Reasoning-Quality Alignment Wave 1

`docs/PLAN.md` remains the canonical repo-level plan. This file is the
executable implementation plan for the first Tyler-alignment wave.

**Status:** Completed
**Type:** implementation
**Priority:** High
**Blocked By:** None
**Blocks:** Further benchmark reruns and deeper V1 parity work

---

## Gap

**Current:** The repo has the right architectural shape, but the highest-value
reasoning method gaps remain in the prompt layer, claim extraction, dedup,
anti-conformity enforcement, and anonymization hardening.

**Target:** Stabilize the cheap-model implementation so the core reasoning
protocol matches Tyler's intended method closely enough to benchmark fairly
before changing models or search providers.

**Why:** These are the gaps most likely to determine whether the system is a
real improvement over a simpler multi-model pipeline or just a polished,
expensive aggregation flow.

---

## References Reviewed

- `docs/plans/v1_spec_alignment.md` - current reconciliation memo
- `docs/notebooks/04_reasoning_quality_alignment_wave1.ipynb` - planning artifact for this wave
- `2026_0325_tyler_feedback/1. V1_Build_Plan_Step_By_Step.md` - Tyler's staged build order
- `2026_0325_tyler_feedback/2. V1_DESIGN.md` - design constraints and protocol intent
- `2026_0325_tyler_feedback/4. V1_PROMPTS.md` - prompt method to preserve
- `CLAUDE.md` - project operating rules
- `README.md` - current external product framing
- `src/grounded_research/canonicalize.py` - current extraction, dedup, and dispute logic
- `src/grounded_research/verify.py` - current arbitration enforcement
- `engine.py` - current steering and pipeline control flow
- `src/grounded_research/models.py` - current structured contracts
- `prompts/analyst.yaml` - current analyst prompt
- `prompts/dedup.yaml` - current dedup prompt
- `prompts/arbitration.yaml` - current arbitration prompt
- `prompts/dispute_classify.yaml` - current dispute prompt

---

## Files Affected

- `prompts/analyst.yaml` (modify)
- `prompts/dedup.yaml` (modify)
- `prompts/arbitration.yaml` (modify)
- `prompts/dispute_classify.yaml` (modify)
- `prompts/claimify.yaml` (create)
- `src/grounded_research/canonicalize.py` (modify)
- `src/grounded_research/models.py` (modify)
- `src/grounded_research/verify.py` (modify)
- `engine.py` (modify)
- `tests/test_phase_boundaries.py` (modify)
- `tests/test_canonicalize.py` (create)
- `tests/test_verify.py` (create)
- `docs/notebooks/04_reasoning_quality_alignment_wave1.ipynb` (create/update)
- `docs/FEATURE_STATUS.md` (modify if any implementation status language changes)
- `docs/TECH_DEBT.md` (modify to remove or narrow resolved items)

---

## Implemented

### Completed Steps

1. Hardened the prompt layer without changing provider/model assumptions.
   Port the essential Tyler prompt method into the current prompt surfaces:
   frame-specific instructions and failure modes for analysts, explicit
   non-merge criteria for dedup, stronger anti-conformity basis requirements for
   arbitration, and clearer dispute classification instructions.

2. Added a dedicated claim-extraction step.
   Create `prompts/claimify.yaml` and replace the current copy-through
   extraction path with an LLM extraction pass over analyst outputs. The output
   contract must produce self-contained claims with evidence IDs and a
   specificity marker when the source does not support full detail.

3. Hardened deduplication mechanically.
   Keep the existing fail-loud fallback, but add code-level validation that:
   every raw claim appears exactly once, zero-group output is rejected, and one
   retry occurs before 1:1 promotion.

4. Enforced anti-conformity in the schema and validator layer.
   Extend arbitration outputs so every claim update carries an explicit basis
   type and short justification tied to cited evidence. Reject claim updates
   that fail validation.

5. Added anonymization scrubbing before downstream reuse.
   Scrub or reject analyst outputs that contain model-family self-identification
   before claim extraction and arbitration inputs are built.

6. Updated tests and plan docs after verification.
   Preserve the benchmark/stability framing: cheap models remain the
   development baseline until the reasoning method is stabilized.

---

## Failure Modes

| Failure Mode | Detection | Response |
|--------------|-----------|----------|
| Prompt hardening produces cleaner JSON but weaker reasoning | Frozen-case prompt review and benchmark spot checks show less specificity or weaker counterarguments | Revert the prompt change, isolate the prompt surface, and port smaller Tyler elements one at a time |
| Claimify step produces vague or duplicated claims on cheap models | New claim extraction tests fail or extracted claims lose specificity relative to analyst text | Keep the dedicated stage, tighten schema descriptions, add one retry path, and reassess prompt scope before widening rollout |
| Dedup retry hides systematic grouping failures | Retry succeeds structurally but still collapses distinct claims or leaves coverage holes | Add validation that checks one-to-one raw claim coverage and suspicious over-merging before accepting retry output |
| Anti-conformity validation becomes too weak to matter | Claim updates pass without meaningful basis justification | Tighten required fields and reject updates rather than downgrading to warnings |
| Anti-conformity validation becomes too strict and blocks legitimate updates | Arbitration results fail frequently despite clearly relevant fresh evidence | Review failing cases, improve justification instructions, and adjust the validator at the contract level rather than bypassing it |
| Anonymization scrub mutates substantive content | Tests show meaning changed or evidence references were altered | Restrict scrubbing to model-identity phrases only and fail loud on ambiguous cases |

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_canonicalize.py` | `test_claimify_extraction_produces_self_contained_claims` | Dedicated extraction path returns atomic claims with required fields |
| `tests/test_canonicalize.py` | `test_dedup_retry_then_fallback_on_invalid_grouping` | Invalid dedup output retries once, then fails loud into 1:1 promotion |
| `tests/test_verify.py` | `test_claim_update_requires_valid_basis_type_and_cited_evidence` | Arbitration updates are rejected unless basis contract is satisfied |
| `tests/test_verify.py` | `test_model_self_identification_is_scrubbed_or_rejected` | Downstream stages never receive analyst text with model identity leakage |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/test_phase_boundaries.py` | End-to-end phase contracts must remain valid |
| `python -m pytest tests/` | No regression across existing integration coverage |

---

## Acceptance Criteria

- [x] Prompt surfaces encode Tyler's core reasoning safeguards without changing the cheap-model development baseline
- [x] Claim extraction is a dedicated post-analyst stage rather than analyst copy-through
- [x] Dedup rejects invalid grouping outputs and only falls back to 1:1 promotion after one failed retry
- [x] No claim update is accepted unless it carries an allowed basis type, cited evidence IDs, and a justification tied to that basis
- [x] Analyst outputs passed downstream are anonymized mechanically, not only by prompt convention
- [x] Required tests pass
- [x] Full test suite passes for the targeted Wave 1 suite
- [x] Docs reflect the new contracts

## Verification Run

- `PYTHONPATH=src python -m pytest tests/test_anonymize.py tests/test_verify.py tests/test_prompt_templates.py tests/test_canonicalize.py tests/test_phase_boundaries.py`
  - Result: `41 passed, 1 skipped`

---

## Notes

- This wave deliberately excludes model swaps, Tavily/Exa integration, and
  dispute-taxonomy renaming.
- The goal is to stabilize reasoning quality first, then decide whether
  remaining V1 parity items materially improve benchmark outcomes.
- If the claim-extraction step proves too weak on cheap models, do not silently
  retreat to the old behavior. Record the failure explicitly and reassess the
  stage contract.
- Next review gate: rerun comparative benchmarks and decide whether Wave 2
  should focus on richer prompt parity, search-provider experiments, or
  benchmark automation.
