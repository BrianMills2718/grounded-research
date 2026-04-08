# Tyler Audit Failure Analysis

This file explains what went wrong in the earlier Tyler review cycle, how the
current audit corrects it, and what controls now prevent the same failure mode
from recurring.

If this file conflicts with `docs/TYLER_SPEC_GAP_LEDGER.md`, trust the ledger
for the current clause-level truth.

## Purpose

Use this document for three things:

1. classify why earlier Tyler status claims were wrong or premature,
2. define the intake and verification workflow for new findings,
3. define the controls required before any future parity or closure claim.

## What Went Wrong Previously

### 1. Contract Migration Was Mistaken For Full Spec Compliance

The repo completed a real Tyler-native runtime and export cutover. That was a
necessary milestone, but it was later treated as if it proved clause-by-clause
Tyler compliance.

Failure pattern:

- runtime artifacts became Tyler-shaped,
- several compatibility surfaces were deleted,
- parity docs then overclaimed closure before every Tyler clause had been
  tested against live code.

Consequence:

- real orchestration and policy gaps remained in Stage 1, Stage 2, Stage 3,
  Stage 4, Stage 5, and Stage 6 even after the migration waves were complete.

### 2. Prompt And Schema Review Was Too Narrow

Earlier review work focused heavily on:

- prompt literalness,
- schema literalness,
- current-vs-Tyler type surfaces.

That was useful, but it missed a different class of divergence:

- orchestration order,
- routing logic,
- model assignment policy,
- round caps,
- evidence-context assembly,
- randomization requirements.

Consequence:

- the repo could claim "prompt literalness closed" while still violating
  Tyler's Stage 5 query roles or Stage 6a sequencing in live code.

### 3. Behavioral Verification Was Underspecified

Several earlier claims were based on static reading or landed plans rather than
behavior-backed checks.

Examples of what needed dynamic verification:

- whether Stage 6a actually sees the post-Stage-5 dispute queue,
- whether Stage 5 sources actually enter Stage 6 synthesis context,
- whether arbitration rounds are really capped at Tyler's limit,
- whether prompt order is actually randomized at runtime.

Consequence:

- the docs could say a behavior existed while the live code path still skipped
  or violated it.

### 4. Local And Shared-Infra Gaps Were Not Separated Early Enough

Some Tyler requirements depend on shared infrastructure:

- Tavily control surfaces,
- Exa control surfaces,
- frontier-model parity,
- provider-specific schema behavior.

Earlier review waves did not always separate:

- local repo divergences that `grounded-research` can patch now,
- shared-infra blockers that belong in `open_web_retrieval`, `llm_client`, or
  `prompt_eval`.

Consequence:

- status docs blurred "open local bug" and "external dependency",
- remediation sequencing was harder to reason about.

### 5. Authority Docs Were Allowed To Drift Ahead Of Evidence

Several documents summarized parity or closure before the repo had:

- a clause inventory,
- a canonical finding ledger,
- an owner/action classification for each gap.

Consequence:

- historical wave summaries became misleading when treated as current truth.

## Root-Cause Taxonomy

Every new Tyler finding should be explainable by one or more of these causes.

### A. `evidence_gap`

The earlier claim lacked a clause anchor, code evidence, or behavior check.

### B. `layer_confusion`

The review checked prompts or schemas but not the runtime orchestration layer
that actually determines behavior.

### C. `boundary_confusion`

A shared-infra requirement was treated as if it were owned locally, or a local
bug was hand-waved as external.

### D. `status_overclaim`

A wave-completion note or summary doc was promoted to current truth without the
ledger proving clause-by-clause closure.

### E. `verification_gap`

The claim described behavior that had not been demonstrated through a test,
prompt render, CLI path, or live smoke.

## Current Corrective Structure

The repo now uses a layered process:

1. `docs/plans/tyler_spec_gap_audit_wave1.md`
   - defines how findings must be audited
2. `docs/TYLER_SPEC_GAP_LEDGER.md`
   - canonical clause-level truth
3. `docs/plans/tyler_gap_remediation_wave1.md`
   - converts verified local rows into implementation order
4. `docs/TYLER_EXECUTION_STATUS.md`
   - high-level required/extension/blocked status surface
5. this file
   - explains prior review failure modes and the controls that now apply

## Required Intake Workflow For New Findings

Any new finding from Tyler, another reviewer, or an external audit must follow
this flow.

### Step 1: Normalize The Claim

Convert the prose claim into one Tyler clause.

Required output:

- exact Tyler source file and section,
- one-sentence requirement,
- stable `spec_id`.

### Step 2: Map The Local Surface

Identify the exact symbol, prompt, config field, or CLI path that implements
or violates the clause.

Do not stop at a whole file if a narrower symbol can be named.

### Step 3: Verify The Evidence

Choose the smallest verification path that can prove or falsify the claim:

- code line reference,
- prompt render diff,
- targeted unit test,
- phase-boundary test,
- CLI path,
- shared-infra smoke.

### Step 4: Classify The Row

Allowed classes:

- `literal`
- `local_divergence`
- `extension`
- `stale_doc`
- `shared_infra_blocked`
- `tyler_ambiguity`

### Step 5: Assign Owner And Action

Every open row must have:

- one owner,
- one next action.

No multi-owner ambiguity in the ledger.

### Step 6: Reconcile Authority Docs

If the new row changes the repo's status story, update:

- `docs/TYLER_EXECUTION_STATUS.md`
- `docs/PLAN.md`
- `docs/ROADMAP.md`
- `docs/plans/CLAUDE.md`

Historical documents must either be updated or explicitly marked as superseded
by the ledger.

## Prevention Controls

These controls are now mandatory.

### 1. Ledger-First Truth

No future claim like:

- "Tyler parity is complete"
- "prompt literalness is closed"
- "repo-local work is done"

is allowed unless the supporting clauses are recorded as `literal`,
`extension`, `shared_infra_blocked`, or `tyler_ambiguity` in the ledger.

### 2. No Closure Claims From Migration Alone

Completing a refactor, cutover, or deletion wave is not enough to claim Tyler
compliance. Migration and compliance are different questions.

### 3. Behavior Claims Need Behavior Checks

Any claim about:

- ordering,
- routing,
- round limits,
- user steering,
- evidence propagation,
- randomization,
- live provider behavior

must cite a real verification path.

### 4. Shared Boundaries Must Be Named Early

If a requirement depends on shared infrastructure, classify it that way
immediately. Do not bury shared blockers inside local wave prose.

### 5. Historical Docs Cannot Compete With The Ledger

If a historical wave summary becomes stale, it must:

- say so explicitly,
- and defer to the ledger or current status doc.

### 6. Remediation Plans Must Cite Ledger Rows

No implementation wave should open on vague prose like "fix Tyler gaps."
Every remediation phase must cite the exact `spec_id` rows it addresses.

### 7. Root Cause Must Be Recorded For Significant Misses

For every `critical` or `high` row that contradicts a previous closure claim,
record at least one root-cause tag from the taxonomy above. This turns the
audit into process improvement, not just a bug list.

## Recommended Organization Views

The ledger is canonical, but review work should be organized in four views:

1. by stage
   - Stage 1 through Stage 6
2. by owner
   - `grounded-research`, `open_web_retrieval`, `llm_client`, `prompt_eval`,
     `docs-only`
3. by severity
   - `critical`, `high`, `medium`, `low`
4. by root cause
   - `evidence_gap`, `layer_confusion`, `boundary_confusion`,
     `status_overclaim`, `verification_gap`

This prevents the repo from solving only one dimension of the problem.

## Exit Standard Going Forward

The repo may say a Tyler area is "closed" only when:

1. the relevant clauses are represented in the ledger,
2. each clause has evidence and classification,
3. local divergences are either fixed or intentionally open,
4. shared blockers are explicitly assigned,
5. current authority docs match the ledger-backed status.
