# Tyler Spec Gap Audit Wave 1

`docs/PLAN.md` remains the canonical repo-level plan. This file defines the
systematic review protocol for auditing the live codebase against Tyler's V1
spec packet.

**Status:** Planned
**Type:** design
**Priority:** High
**Blocked By:** None
**Blocks:** Any future "spec violation" implementation wave

---

## Gap

**Current:** The repo has Tyler status notes, parity audits, and remainder
plans, but no single clause-by-clause audit protocol that can convert a claim
like "the code violates the spec" into a reproducible, evidence-backed gap
ledger.

**Target:** A disciplined review method that maps each Tyler requirement to:

- the exact source clause in the Tyler packet,
- the exact local code and doc surfaces that implement it,
- a verdict with a narrow classification,
- the exact remediation owner and next action.

**Why:** Without a clause ledger, "many violations" turns into an argument about
interpretation. The audit needs to separate:

- real local divergence,
- additive local behavior,
- stale docs,
- Tyler-internal ambiguity,
- shared-infra blockers.

---

## References Reviewed

- `CLAUDE.md` - project operating rules; Tyler literal compliance is the top priority.
- `docs/PLAN.md` - current canonical plan and active surfaces.
- `docs/ROADMAP.md` - current frontier and shared-infra boundary.
- `docs/plans/CLAUDE.md` - plan index and current active plan surface.
- `docs/plans/tyler_faithful_execution_remainder.md` - what the project currently claims is still open.
- `docs/TYLER_EXECUTION_STATUS.md` - strict required/extension/blocked checklist.
- `docs/TYLER_LITERAL_PARITY_AUDIT.md` - current repo-local parity claim.
- `docs/TYLER_PROMPT_LITERALNESS_MATRIX.md` - line-by-line prompt audit precedent.
- `tyler_response_20260326/1. V1_Build_Plan_Step_By_Step (1).md` - Tyler implementation contract.
- `tyler_response_20260326/2. V1_DESIGN (1).md` - Tyler architecture and policy contract.
- `tyler_response_20260326/3. V1_SCHEMAS (1).md` - Tyler typed schema contract.
- `tyler_response_20260326/4. V1_PROMPTS (1).md` - Tyler prompt contract.

---

## Files Affected

- `docs/plans/tyler_spec_gap_audit_wave1.md` (create)
- `docs/notebooks/33_tyler_spec_gap_audit_wave1.ipynb` (create)
- `docs/TYLER_SPEC_GAP_LEDGER.md` (create)
- `docs/plans/tyler_faithful_execution_remainder.md` (modify)
- `docs/plans/CLAUDE.md` (modify)
- `docs/PLAN.md` (modify)
- `docs/ROADMAP.md` (modify)

---

## Audit Rules

### Canonical Inputs

The audit must treat these as authoritative, in this order:

1. Tyler packet:
   - Build Plan
   - Design
   - Schemas
   - Prompts
2. Live code in `src/`, `engine.py`, `prompts/`, and `config/`
3. Active authority docs:
   - `CLAUDE.md`
   - `docs/PLAN.md`
   - `docs/ROADMAP.md`
   - `docs/TYLER_EXECUTION_STATUS.md`

### Required Evidence For Every Finding

Every recorded gap must include:

1. `spec_id`
   - stable local identifier like `S2-PROMPT-QUERY-DATED-001`
2. `tyler_source`
   - exact Tyler file and section
3. `tyler_requirement`
   - one sentence, quoted or tightly paraphrased
4. `local_surface`
   - exact file path and symbol/function/config surface
5. `evidence`
   - exact lines, behavior, or failing verification
6. `classification`
   - one of:
     - `literal`
     - `local_divergence`
     - `extension`
     - `stale_doc`
     - `shared_infra_blocked`
     - `tyler_ambiguity`
7. `severity`
   - `critical`, `high`, `medium`, `low`
8. `owner`
   - `grounded-research`, `open_web_retrieval`, `llm_client`, `prompt_eval`, or `docs-only`
9. `next_action`
   - `patch_local`, `open_shared_plan`, `document_extension`, `close_no_action`

No finding counts if any of those fields are missing.

### Classification Policy

- `literal`: local implementation matches Tyler closely enough to accept
  literally.
- `local_divergence`: Tyler requires something different and this repo can fix
  it locally.
- `extension`: local behavior goes beyond Tyler without conflicting with Tyler.
- `stale_doc`: code is fine, docs are wrong.
- `shared_infra_blocked`: Tyler requires it, but the real owner is shared infra.
- `tyler_ambiguity`: Tyler's own materials conflict or underspecify the result.

### Review Order

Audit in this order so the highest-value drift is found first:

1. stage contracts and schemas
2. stage prompts and deterministic orchestrator templates
3. live runtime wiring and config defaults
4. output artifacts and CLI behavior
5. docs and status claims
6. shared-infra assumptions Tyler requires

---

## Plan

### Phase 1: Build The Clause Inventory

Create a stage-by-stage inventory of Tyler requirements from the four spec
files.

Deliverables:

- clause inventory grouped by Stage 1 through Stage 6
- stable `spec_id` values
- explicit shared assumptions (providers, models, budgets, statuses)

Pass if:

- every audit row is traceable to one Tyler clause
- no stage is skipped

Failure modes:

- vague categories without exact Tyler anchors
- mixing build-plan guidance with runtime facts without tagging the source

### Phase 2: Map Each Clause To Local Surfaces

For every Tyler clause, identify the exact live local implementation surface.

Deliverables:

- local file/symbol mapping for each clause
- "no local owner" explicitly marked where shared infra owns the behavior

Pass if:

- each clause has at least one mapped surface or an explicit external owner

Failure modes:

- findings that cite a whole file instead of the exact symbol or config surface
- doc-only claims with no code reference

### Phase 3: Evaluate And Record Verdicts

Review each clause against code and record the verdict in the ledger.

Deliverables:

- `docs/TYLER_SPEC_GAP_LEDGER.md`
- explicit counts by classification and owner

Pass if:

- every row has the required evidence fields
- no open claim remains unclassified

Failure modes:

- opinion-only findings
- "violates spec" claims without code evidence
- hidden additive behavior mislabeled as Tyler-required

### Phase 4: Verify Disputed Findings

Any row whose verdict depends on behavior rather than static text must have a
verification method.

Verification methods may include:

- targeted unit tests
- prompt render diffs
- config inspection
- CLI output checks
- live provider smoke tests in shared infra

Pass if:

- behavior-based findings cite a real verification path

Failure modes:

- behavioral accusations based only on code reading
- shared-infra findings assigned locally without testing the shared boundary

### Phase 5: Produce Remediation Waves

Turn the ledger into executable next steps grouped by owner.

Deliverables:

- local patch wave(s) for `grounded-research`
- shared follow-through wave(s) for `open_web_retrieval`, `llm_client`,
  `prompt_eval`
- docs-only cleanup wave where appropriate

Pass if:

- every open gap has a named owner and next action
- the repo can distinguish "fix now" from "document and defer"

Failure modes:

- mixing shared-infra and local fixes in one wave
- reopening already-deleted legacy runtime modes

---

## Required Tests

### New Checks

| Test / Check | What It Verifies |
|--------------|------------------|
| Notebook JSON parse | Planning artifact is valid and readable |
| Ledger completeness review | Every finding has the required evidence fields |
| Spot verification per behavioral finding | Dynamic claims are backed by a real check |

### Existing Checks (Must Still Hold)

| Check | Why |
|-------|-----|
| `docs/plans/CLAUDE.md` stays aligned with the current active review wave | One current planning authority |
| `docs/PLAN.md` and `docs/ROADMAP.md` reflect the same current frontier | Avoid stale authority drift |

---

## Acceptance Criteria

- [ ] A clause inventory exists for Tyler Stages 1 through 6 plus shared assumptions.
- [ ] `docs/TYLER_SPEC_GAP_LEDGER.md` exists and uses the required evidence fields.
- [ ] Every claimed violation is classified as literal, local divergence, extension, stale doc, shared-infra blocked, or Tyler ambiguity.
- [ ] Every open gap has an owner and next action.
- [ ] Active plan surfaces point at this audit wave instead of vague future review language.

---

## Notes

- This wave is review-first. It does not pre-approve implementation changes.
- Additive local behavior may remain if it does not conflict with Tyler and is
  documented clearly as an extension.
- If the audit proves a local schema or call-site mismatch, the follow-up plan
  should patch local code to match Tyler rather than documenting the mismatch
  away.
