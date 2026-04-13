# Tyler Full Spec Exhaustive Audit Wave 1

**Status:** Active
**Type:** audit plan
**Priority:** High
**Parent plan:** `docs/plans/tyler_faithful_execution_remainder.md`

## Goal

Audit every specification unit in Tyler's four canonical V1 source files
against the live `grounded-research` codebase and authority docs.

This wave is stricter than the earlier stage-oriented audit work. It is not
"review the major stages again." It is:

1. enumerate every Tyler source section,
2. split every normative section into explicit audit units,
3. map each audit unit to local code, config, prompts, tests, CLI behavior, or
   docs,
4. verify every unit with the minimum valid evidence type,
5. record every finding in the canonical ledger.

## Canonical Tyler Sources

The source packet for this wave is fixed:

1. `2026_0325_tyler_feedback/1. V1_Build_Plan_Step_By_Step.md`
2. `2026_0325_tyler_feedback/2. V1_DESIGN.md`
3. `2026_0325_tyler_feedback/3. V1_SCHEMAS.md`
4. `2026_0325_tyler_feedback/4. V1_PROMPTS.md`

No alternate packet, paraphrase doc, or historical summary may override those
four files for this audit.

## Why A New Wave Exists

The repo already has:

- `docs/TYLER_SPEC_GAP_LEDGER.md`
- `docs/TYLER_SYSTEMATIC_REVIEW_MATRIX.md`
- `docs/plans/tyler_spec_gap_audit_wave1.md`

Those were enough to drive the initial clause-by-clause correction wave.
They are not yet the same thing as an exhaustive packet audit.

The missing layer is:

- one audit inventory that proves every Tyler source section has been touched,
- one explicit rule for splitting narrative sections into normative audit
  units,
- one tracker that can answer "what in Tyler's packet has not yet been audited?"

## Scope

In scope:

- every normative Tyler requirement in the four canonical source files
- every Tyler source heading and subheading, even if the outcome is "context
  only"
- live code, prompts, config, tests, CLI/output artifacts, and active docs
- shared-infra assumptions only where `grounded-research` depends on them

Out of scope:

- implementing fixes before the corresponding audit unit exists
- broad benchmark expansion
- speculative cleanup unrelated to a Tyler audit unit

## Pre-Made Decisions

1. This wave audits **every Tyler source section**, not just the sections that
   previously produced gaps.
2. Every source heading gets an audit row in
   `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md`.
3. Every normative requirement under a heading becomes one or more explicit
   `audit_unit_id`s.
4. Narrative-only material is still tracked, but may resolve to:
   - `context_only`
   - `design_intent_only`
   instead of a code-mapped gap.
5. Findings still land only in `docs/TYLER_SPEC_GAP_LEDGER.md`; the new matrix
   is coverage tracking, not a second findings ledger.
6. Static structure claims may close by inspection. Behavior claims require one
   of:
   - targeted unit/integration test,
   - prompt render,
   - CLI path,
   - trace/artifact inspection,
   - provider/request verification.
7. Shared-infra assumptions are audited from the consuming boundary first.
8. Historical Tyler summary docs never count as proof for this wave.

## Audit Unit Definition

An audit unit is the smallest Tyler requirement that can receive one verdict.

Valid audit unit kinds:

- `stage_rule`
- `schema_contract`
- `enum/value_contract`
- `prompt_template`
- `orchestrator_template`
- `branch_or_skip_rule`
- `model_role_rule`
- `output_contract`
- `anti_pattern_prohibition`
- `cross_cutting_rule`
- `context_only`

Split headings into multiple audit units when one heading contains multiple
independent requirements.

## Required Artifacts

This wave creates or updates:

1. `docs/plans/tyler_full_spec_exhaustive_audit_wave1.md`
2. `docs/notebooks/48_tyler_full_spec_exhaustive_audit_wave1.ipynb`
3. `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md`
4. `docs/TYLER_SPEC_GAP_LEDGER.md`
5. `docs/TYLER_SYSTEMATIC_REVIEW_MATRIX.md` only if a new finding requires a
   fresh focused review lane
6. authority docs only after the ledger changes

## Matrix Contract

`docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md` is the coverage tracker for this wave.

Each row must include:

- `audit_unit_id`
- `source_doc`
- `source_section`
- `unit_kind`
- `tyler_audit_intent`
- `evidence_kind`
- `coverage_status`
- `ledger_rows`
- `notes`

Allowed `coverage_status` values:

- `pending`
- `in_progress`
- `audited_no_gap`
- `audited_gap_recorded`
- `audited_context_only`
- `blocked_shared`

## Ledger Rule

The matrix answers:

- has this Tyler source unit been audited?

The ledger answers:

- what did we find?

Do not record prose findings in the matrix. Do not use the ledger as a
coverage tracker.

## Phases

### Phase 1: Freeze The Full Source Inventory

Deliverables:

- one row per Tyler source heading/subheading in
  `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md`
- stable `audit_unit_id` naming scheme by source file and section

Pass if:

- every heading from all four Tyler source files appears in the matrix
- no source file is only partially inventoried

Failure modes:

- skipping subheadings
- mixing multiple unrelated sections into one row

### Phase 2: Split Normative Sections Into Audit Units

Deliverables:

- sections with multiple requirements split into explicit audit units
- narrative-only sections marked `context_only`

Pass if:

- each row can receive one verdict without ambiguity

Failure modes:

- "mega rows" that hide multiple independent requirements
- context sections incorrectly treated as code requirements

### Phase 3: Map Audit Units To Local Surfaces

Deliverables:

- exact local surface mapping for every non-context audit unit
- shared owner named where no local surface should exist

Pass if:

- each audit unit has at least one exact symbol/path/config/doc surface or a
  justified shared owner

Failure modes:

- file-level handwaving instead of exact symbols
- local/shared ownership confusion

### Phase 4: Verify Every Unit

Deliverables:

- evidence attached for every audited unit
- behavior-backed units cite runtime evidence, not only inspection

Pass if:

- no audited behavior unit lacks a verification path

Failure modes:

- static-only closure of routing/order/propagation claims
- provider behavior claimed without request/runtime evidence

### Phase 5: Populate Ledger Gaps

Deliverables:

- every real divergence added to `docs/TYLER_SPEC_GAP_LEDGER.md`
- every matrix row points to the right ledger row(s) or `none`

Pass if:

- no real finding remains only in a plan or notebook

Failure modes:

- matrix and ledger drift
- stale prose-only findings

### Phase 6: Reconcile Authority Docs

Deliverables:

- status/plan/roadmap docs updated only after the ledger changes

Pass if:

- authority docs do not outrun audit evidence

Failure modes:

- summary docs declare closure before source coverage is complete

### Phase 7: Produce Remediation And Watch Outputs

Deliverables:

- local remediation wave(s)
- shared follow-through wave(s)
- docs-only cleanup wave(s)
- operational watch items separated from active implementation gaps

Pass if:

- every unresolved audit result has an explicit next action type

Failure modes:

- unresolved findings with no owner
- mixing active blockers and operational watch items

## Verification

Minimum verification for this wave:

1. `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md` covers all four Tyler source files
2. every row has an `audit_unit_id` and evidence type
3. every real finding lands in `docs/TYLER_SPEC_GAP_LEDGER.md`
4. authority docs are updated only after ledger-backed changes
5. notebook JSON parses cleanly

## Failure Modes

| Failure mode | Symptom | Required response |
|---|---|---|
| Partial packet audit | one Tyler source file or section missing from the matrix | add the missing rows before continuing |
| Over-broad audit units | one row mixes multiple requirements | split the row before judging it |
| Context confusion | narrative section treated as a code bug | mark `context_only` and move on |
| Behavior without evidence | routing/order/randomization claim lacks runtime proof | add a test, trace check, or CLI/provider verification |
| Ledger drift | findings appear in prose but not ledger | write the ledger row immediately |
| Status overclaim | summary docs move ahead of coverage or ledger | fix docs in the same change set |

## Todo List

- [ ] Phase 1: freeze the full source inventory
- [ ] Phase 2: split normative sections into audit units
- [ ] Phase 3: map audit units to local surfaces
- [ ] Phase 4: verify every unit
- [ ] Phase 5: populate ledger gaps
- [ ] Phase 6: reconcile authority docs
- [ ] Phase 7: produce remediation and watch outputs

## Completion Condition

This wave is complete only when:

- every Tyler source section has a matrix row,
- every non-context audit unit has been audited,
- every real finding is in the ledger,
- and the repo can answer, mechanically and truthfully:
  - what Tyler specified,
  - where it lives locally,
  - what evidence was checked,
  - what still diverges,
  - and what happens next.
