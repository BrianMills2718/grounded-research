# Tyler Prompt Literalness Wave 1

**Status:** Active
**Type:** repo-local implementation
**Priority:** High
**Parent plan:** `docs/plans/tyler_faithful_execution_remainder.md`

## Goal

Close the remaining repo-local prompt-literalness gap against Tyler's
`tyler_response_20260326/4. V1_PROMPTS (1).md` for the active unresolved
surfaces:

- Stage 1 decomposition
- Stage 2 query diversification
- Stage 2 finding extraction
- Stage 5 neutral verification query generation

This wave is specifically about **exact prompt/orchestrator literalness**, not
about reopening runtime contracts or adding alternate prompt families.

## Why This Needs Its Own Wave

The remaining Tyler gap is no longer stage contracts. It is prompt/orchestrator
fidelity:

- Stage 1 and Stage 2 prompt files are close to Tyler but not yet audited
  line by line
- Stage 5 verification query generation is still implemented as a short
  deterministic helper in `verify.py`, while Tyler's source defines it as an
  explicit orchestrator template with named query roles and recency-sensitive
  logic

Without closing this, "faithfully executed Tyler" remains an overclaim.

## Scope

In scope:

- `prompts/tyler_v1_decompose.yaml`
- `prompts/tyler_v1_query_diversification.yaml`
- `prompts/tyler_v1_extract_findings.yaml`
- Stage 5 neutral verification query generation in:
  - `src/grounded_research/verify.py`
  - `prompts/verification_queries.yaml` or a renamed Tyler-native replacement
- docs that classify the audited results
- tests for Stage 5 query-generation behavior and prompt render/wiring

Out of scope:

- Tavily/Exa provider implementation
- frontier-model parity
- frozen eval expansion beyond one case
- any return of legacy runtime modes

## Pre-Made Decisions

1. Tyler's source markdown is the contract for this wave.
2. "Literal" means:
   - line-by-line prompt parity where the source is a model prompt
   - line-by-line template/behavior parity where the source is an orchestrator
     template
3. Stage 5 query generation will remain code-owned orchestrator behavior, but it
   must be rewritten to reflect Tyler's explicit neutral/supporting/authoritative
   query roles and recency-sensitive rule.
4. If a Tyler instruction cannot be implemented literally because it depends on
   shared provider features, the repo must:
   - preserve the instruction in the local prompt/template where possible, and
   - document the exact shared-infra dependency explicitly
5. Do not create an alternate runtime profile for prompt comparisons in
   `grounded-research`. The live prompt family remains Tyler-literal; any
   comparison stays in `prompt_eval`.
6. Rename `prompts/verification_queries.yaml` only if that improves clarity
   without creating migration ambiguity. Otherwise keep the path and make the
   content Tyler-literal.

## Acceptance Criteria

This wave passes only if:

1. each of the four targeted prompt/orchestrator surfaces has a line-by-line
   audit result,
2. every repo-local divergence is either patched or documented as a justified
   non-local dependency,
3. Stage 5 query generation behavior matches Tyler's intended roles:
   - neutral question
   - weaker-position support query
   - authoritative-source query
   - dated search only when recency-sensitive
4. tests prove the Stage 5 builder/template behavior structurally,
5. authority docs say exactly what remains after this wave.

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| audit is superficial | broad “close enough” claims with no line-level findings | fail the wave; produce a real diff-style audit |
| Stage 5 remains hand-wavy | helper still emits generic `evidence` / `versus` / `official study` strings | rewrite builder/template around Tyler’s explicit query roles |
| provider-specific assumptions blur the scope | local code tries to implement Tavily/Exa adapters here | stop; record as shared-infra dependency instead |
| prompt patches drift from schema/runtime | prompt text becomes more literal but no longer matches current call sites or schema inputs | patch call sites and tests in the same wave |

## Phases

### Phase 1: Produce The Literalness Matrix

Deliverables:

- a diff-style audit for:
  - Stage 1 decomposition prompt
  - Stage 2 query diversification prompt
  - Stage 2 finding extraction prompt
  - Stage 5 neutral verification query template/behavior

Pre-made decisions:

- compare against the exact Tyler sections in
  `tyler_response_20260326/4. V1_PROMPTS (1).md`
- classify each line/block as:
  - identical
  - adapted but acceptable
  - local deviation to patch
  - shared-infra dependency

Pass if:

- the audit is specific enough that another agent could patch from it without
  re-reading the whole Tyler document

### Phase 2: Patch Stage 1 And Stage 2 Prompts

Deliverables:

- updated `tyler_v1_decompose.yaml`
- updated `tyler_v1_query_diversification.yaml`
- updated `tyler_v1_extract_findings.yaml`
- prompt render tests if needed

Pass if:

- any remaining differences are genuinely schema/runtime-driven and documented

### Phase 3: Literalize Stage 5 Query Generation

Deliverables:

- rewritten Stage 5 query-generation logic in `verify.py`
- prompt/template surface for verification query generation aligned with Tyler
- tests covering:
  - neutral-question framing
  - weaker-position support query
  - authoritative-source targeting
  - dated-search behavior for recency-sensitive claims

Pre-made decisions:

- Stage 5 query generation remains orchestrator logic, not a model call
- the implementation may use a renderable template plus code-owned inputs, or a
  pure deterministic builder, as long as the emitted behavior is Tyler-literal
- recency-sensitive logic must be explicit and configurable, not implied

Pass if:

- the builder/template output is structurally Tyler-like and testable

### Phase 4: Reconcile Docs

Deliverables:

- updated `TYLER_LITERAL_PROMPT_FIDELITY_AUDIT.md`
- updated `TYLER_LITERAL_PARITY_AUDIT.md`
- updated parent plan if needed

Pass if:

- the docs no longer describe prompt literalness as an open vague uncertainty
- any remaining gaps are named precisely

## Verification

Minimum verification for this wave:

1. targeted prompt/render tests
2. targeted Stage 5 query-generation tests
3. stale-pattern grep proving docs no longer claim vague prompt uncertainty when
   the wave closes

## Todo List

- [ ] Phase 1: produce the literalness matrix
- [ ] Phase 2: patch Stage 1 and Stage 2 prompts
- [ ] Phase 3: literalize Stage 5 query generation
- [ ] Phase 4: reconcile docs

## 24h Execution Rule

This wave should be executed continuously until all four phases are closed or a
real architectural concern appears. Do not stop after the audit or after one
verified patch just because the repo now has another rollback point. The todo
list above is the live phase tracker and must stay synchronized with actual
progress.
