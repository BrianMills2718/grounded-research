# Tyler Prompt Literalness Matrix

This is the Phase 1 audit artifact for
`docs/plans/tyler_prompt_literalness_wave1.md`.

Question answered here:

> For the remaining unresolved prompt/orchestrator surfaces, what is literally
> identical to Tyler's source, what is locally divergent, and what is blocked by
> shared-infra boundaries?

## Scope

Compared against:

- `tyler_response_20260326/4. V1_PROMPTS (1).md`

Compared local surfaces:

- `prompts/tyler_v1_decompose.yaml`
- `prompts/tyler_v1_query_diversification.yaml`
- `prompts/tyler_v1_extract_findings.yaml`
- `src/grounded_research/verify.py::_build_tyler_verification_queries`
- `prompts/verification_queries.yaml`

## Classification Legend

- `Identical`: local surface matches Tyler literally enough to leave alone
- `Patch`: local divergence is repo-local and should be changed now
- `Spec ambiguity`: Tyler source is internally inconsistent or underspecified;
  local behavior must pick one interpretation and document it
- `Shared infra`: literalness depends on provider/runtime capabilities outside
  this repo

## Matrix

### Stage 1: Decomposition

**Source section:** Stage 1 system/user prompt in Tyler V1 prompt package.

**Current status:** Mostly aligned, but not exact.

| Surface | Finding | Classification | Action |
|---|---|---|---|
| System body | Core decomposition rules, self-check block, do-not list, and reasoning instruction are already present and close to Tyler wording | Identical enough | leave unless exact textual diff is cheap |
| Shared output protocol block | Local file uses a shortened custom block instead of Tyler's full `SHARED OUTPUT PROTOCOL` text | Patch | replace local shortened block with Tyler-exact wording where schema-compatible |
| User body | Current user prompt matches Tyler structure and context anchoring | Identical enough | leave unless exact textual diff is cheap |

**Notes:**

- This is a true local prompt-file issue, not a shared-infra dependency.

### Stage 2: Query Diversification

**Source section:** Stage 2 query diversification system/user prompt.

**Current status:** Very close to literal.

| Surface | Finding | Classification | Action |
|---|---|---|---|
| System body | Local prompt matches Tyler's query rules and provider-role split closely | Identical enough | leave unless exact textual diff is cheap |
| User body | Local prompt matches Tyler's four query roles and ordering closely | Identical enough | leave unless exact textual diff is cheap |
| Budget note / orchestrator note | Tyler source includes budget/orchestrator commentary outside the prompt body; local runtime enforces query count in code rather than prompt text | Spec ambiguity | document in audit; no prompt patch required unless runtime mismatch appears |

**Notes:**

- This surface appears to need little or no substantive patching.

### Stage 2: Finding Extraction

**Source section:** Stage 2 finding extraction system/user prompt.

**Current status:** Mostly aligned, but not exact.

| Surface | Finding | Classification | Action |
|---|---|---|---|
| System body | Core extraction rules and evidence-label hierarchy are already close to Tyler wording | Identical enough | leave unless exact textual diff is cheap |
| Shared output protocol block | Local file uses a shortened custom block instead of Tyler's `SHARED_OUTPUT_PROTOCOL` insertion | Patch | replace with the Tyler wording that is compatible with the actual schema |
| Reasoning requirement inside shared protocol | Tyler's global shared block says every prompt has a reasoning field, but this Stage 2 extraction schema does not expose one | Spec ambiguity | preserve the non-conflicting shared-output lines; document why the reasoning-field line cannot be literal without changing the schema |
| User body | Current user prompt matches Tyler structure closely | Identical enough | leave unless exact textual diff is cheap |

### Stage 5: Neutral Verification Query Generation

**Source section:** Stage 5 orchestrator template, not a model prompt.

**Current status:** Not literal.

| Surface | Finding | Classification | Action |
|---|---|---|---|
| Live query-generation behavior | Local runtime uses `_build_tyler_verification_queries()` with three generic strings: `evidence`, `versus`, `official study YEAR` | Patch | rewrite builder to emit Tyler's explicit neutral/supporting/authoritative roles |
| Recency-sensitive query behavior | Tyler defines an optional dated query only for recency-sensitive claims; local runtime always emits exactly three fixed queries and has no recency-sensitive branch | Patch | add explicit recency-sensitive branch and make it configurable |
| Position-aware logic | Tyler's template depends on stronger vs weaker position framing; current builder ignores that distinction | Patch | use dispute positions/claim context to generate the weaker-position support query |
| Authoritative targeting | Tyler expects the authoritative query to target the best source class/domain; current builder emits a generic `official study YEAR` string | Patch | generate authoritative-source-focused queries with domain/type hints where available |
| `prompts/verification_queries.yaml` | File exists but the live Stage 5 path does not use it | Patch | either delete it or repurpose it into the literal orchestrator template surface used by tests/docs |
| Tavily-specific parameters | Tyler mentions `search_depth=\"advanced\"` and `chunks_per_source=3` | Shared infra | keep this out of local adapter logic; document ownership in shared infra |

## Summary

The actual patch burden is concentrated in Stage 5.

Stage classification after audit:

1. Stage 1 decomposition: local prompt patch
2. Stage 2 query diversification: likely no substantive patch
3. Stage 2 finding extraction: local prompt patch plus one documented spec ambiguity
4. Stage 5 neutral verification queries: real repo-local rewrite

## Explicit Remaining Questions After Phase 1

These are narrow enough to continue without stopping:

1. For Stage 1 and Stage 2 prompt files, should the patch aim for exact textual
   parity even where the current wording is semantically equivalent?
   - Current user instruction: yes, exact wording where possible.
2. For Stage 5, should `prompts/verification_queries.yaml` become the tested
   local template surface, or should the literal behavior live only in code?
   - Current plan decision: either is acceptable; prefer the simpler surface
     that keeps the runtime unambiguous.
