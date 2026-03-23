# ADR-0006: Question Decomposition Design Decisions

## Status

Accepted

## Context

Phase A of the v2 roadmap adds question decomposition before search and
analysis. Four design decisions needed to be made before implementation.

## Decisions

### 1. Decomposition Model: gemini/gemini-2.5-flash

Decomposition is a single LLM call requiring good reasoning (typed
sub-questions, falsification targets, optimization axes). Use
`gemini/gemini-2.5-flash` — same tier as dispute classification. Not the
cheap lite model (reasoning quality matters) and not the expensive synthesis
model (overkill for a structured output call).

Config key: `models.decomposition: "gemini/gemini-2.5-flash"`

### 2. Config Key: models.decomposition

Standard pattern — every LLM task gets its own config key per existing
convention. Accessed via `get_model("decomposition")`.

### 3. No Backward Compatibility — Always-On, Revert if Bad

Decomposition is always-on. No `--no-decompose` flag. If the feature
doesn't improve output, revert the code. Move forward aggressively,
rollback if it fails.

Rationale: feature flags add complexity for a feature that should either
work or not. A/B testing happens by comparing git versions, not runtime flags.

### 4. Sub-Question ID Format: SQ-{hash8}

Consistent with existing ID conventions: S- (sources), E- (evidence),
C- (claims), D- (disputes), RC- (raw claims). Sub-questions get `SQ-`
prefix with 8-char hash, generated the same way as other IDs.

## Consequences

- `config.yaml` gets a new `models.decomposition` key
- `models.py` gets `QuestionDecomposition` and `SubQuestion` types
- `engine.py` always runs decomposition — no conditional paths
- Sub-question IDs are stable and referenceable across the pipeline
