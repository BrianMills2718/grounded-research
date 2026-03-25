# Uncertainties

Open issues that are real enough to persist, but not yet resolved.

## U1: Draft Implementation Adoption

Question:

- Which committed implementation surfaces should become accepted project state,
  and which should remain hold/discard?

Current evidence:

- committed end-to-end implementation `c57cd2c`
- `engine.py`
- `config/config.yaml`
- prompt files under `prompts/`
- modules under `src/grounded_research/`
- `scripts/phase_minus1.py`

Current posture:

- hold until each draft is reviewed against `docs/PLAN.md`,
  `docs/CONTRACTS.md`, and `src/grounded_research/models.py`

Plan linkage:

- `docs/plans/01_draft-implementation-adoption.md`
- `docs/PLAN.md` "Open Planning Items"

## U2: Phase 4 Execution Target

Question:

- Should v1 planning continue to describe Phase 4 as target-agentic, or should
  the structured Phase 4a/4b stepping-stone be treated as the accepted current
  target until `Phase -1` is proven?

Current evidence:

- the docs describe Phase 4 as ultimately agentic
- the local draft implementation uses the structured stepping-stone approach

Current posture:

- current v1 plan uses structured `Phase 4a/4b`; agentic merge remains a
  future milestone to be scheduled, not a hidden toggle

Plan linkage:

- `docs/PLAN.md` Phase 4 section
- `docs/adr/0004-agentic-verification-and-fail-loud-phase4.md`

## U3: Real Baseline Evidence And Review Rubric

Question:

- Which committed real-source evidence bundle and which committed rubric artifact
  should become the baseline for `Phase -1`?

Current evidence:

- `tests/fixtures/session_storage_bundle.json` is useful for schema review
- it is not a sufficient real-source thesis baseline by itself

Current posture:

- unresolved; add a real-source bundle and explicit rubric before accepting
  `Phase -1` as proven

Plan linkage:

- `docs/PLAN.md` Phase -1 section
- `docs/notebooks/01_adjudication_review_journey.ipynb`
