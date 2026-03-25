# Plan: V1 Gap Closure After Design Clarification

**Source:** Tyler's review of current codebase vs original V1 design
**Status:** Awaiting answers to `docs/QUESTIONS_FOR_TYLER.md`
**Priority:** High

## Why this plan changed

The previous version mixed real implementation gaps with config choices.
Production model picks do not block implementation. The blocking issues are the
ones that change contracts, control flow, and evaluation criteria.

## Design Gates

These answers are required before implementation should start:

1. **Product boundary**
   The repo currently straddles two positions: adjudication-first layer vs full
   end-to-end research system. This changes docs, benchmarks, and failure
   interpretation.
2. **Claim contract**
   Claim precision needs an explicit structural contract before adding retries
   or validators.
3. **Ambiguity and interrupt policy**
   Early clarification vs late surfacing is a control-flow decision, not a
   prompt tweak.
4. **Anti-conformity enforcement**
   "Only change position for valid reasons" needs a schema and validator
   contract.
5. **Acceptance harness**
   Baseline discipline belongs first in an offline benchmark gate, not as an
   arbitrary runtime feature.

## Implementation Work After Clarification

### 1. Claim Precision Enforcement

**Gap:** Claims are often too abstract relative to source detail.
**Planned work:** Add a structured claim-specificity validator plus one retry
path using source excerpts.
**Where:** `canonicalize.py`, `models.py`, new prompt template
**Acceptance:** Defined by the final claim contract, not by an arbitrary
percentage threshold.

### 2. Protocol-Level Anti-Conformity

**Gap:** The current system can cite new evidence IDs without proving the cited
evidence actually justifies the claim update.
**Planned work:** Extend arbitration outputs and add a post-arbitration
validator for each `claim_update`.
**Where:** `verify.py`, `models.py`, new prompt template
**Acceptance:** No claim update is accepted unless it satisfies the agreed
enforcement contract.

### 3. Dedup Reliability

**Gap:** Dedup can return zero groups, forcing 1:1 fallback.
**Planned work:** Keep current fallback, add one retry path, and verify the
dedup model/prompt pair is stable.
**Where:** `canonicalize.py`
**Acceptance:** Zero-group outcomes become rare enough that fallback is
exceptional rather than routine.

### 4. Analyst Anonymization Hardening

**Gap:** Alpha/Beta/Gamma labels exist, but model self-identification should be
mechanically blocked rather than assumed absent.
**Planned work:** Add a post-analyst scrub/validation pass for model identity
phrases.
**Where:** `engine.py`
**Acceptance:** Downstream stages never receive analyst text that identifies the
underlying model family.

### 5. Evaluation Harness

**Gap:** The repo has comparison scripts, but the acceptance gate is not yet
the canonical driver of implementation choices.
**Planned work:** Freeze the benchmark set, baselines, rubric, and pass/fail
threshold in code and docs.
**Where:** comparison scripts, docs, fixtures
**Acceptance:** A failed benchmark run gives an unambiguous no-go result.

## Implementation Order

1. Lock the design gates from `docs/QUESTIONS_FOR_TYLER.md`
2. Implement claim contract enforcement
3. Implement anti-conformity enforcement
4. Harden dedup reliability
5. Harden anonymization
6. Freeze the evaluation harness
