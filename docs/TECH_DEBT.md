# Tech Debt

Known issues not worth fixing now but should be addressed eventually.

## Code Quality

### Inline prompts (code review #4-5)
`collect.py` query generation and `source_quality.py` scoring prompts are
inline Python strings, not YAML templates. Violates CLAUDE.md rule 8
("Prompts as Data"). Won't change output quality but hurts maintainability.

**Files:** `src/grounded_research/collect.py:84-96,114-128`, `src/grounded_research/source_quality.py:73-80`
**Fix:** Move to `prompts/query_generation.yaml` and `prompts/source_scoring.yaml`

### Hardcoded truncation in prompts (code review #12-13)
`synthesis.yaml` caps evidence at `evidence[:30]` and `long_report.yaml`
truncates content at `content[:400]`. Both hardcoded in Jinja2 templates,
not configurable via config.yaml. The two prompts also use different limits
(`[:500]` vs `[:400]`) with no documented reason.

**Files:** `prompts/synthesis.yaml:35`, `prompts/long_report.yaml:188`
**Fix:** Move to `evidence_policy.synthesis_evidence_cap` and `evidence_policy.content_truncation_chars` in config.yaml

### Counterarguments schema fragility (code review #14)
`AnalystRun.counterarguments` has `default_factory=list` AND `min_length=1`.
Works because Pydantic v2 doesn't validate defaults from `default_factory`.
If Pydantic changes this behavior, failed AnalystRun creation (which passes
no counterarguments) will break.

**File:** `src/grounded_research/models.py:412-414`
**Fix:** Use a validator that enforces min_length only when `error is None`

### PhaseTrace post-creation mutation (code review #15)
`engine.py:255` mutates `PhaseTrace.llm_calls` after appending to
`state.phase_traces`. The trace is correct at write time but the mutation
pattern is fragile — any code reading the trace between append and mutation
would see wrong data.

**File:** `engine.py:255`
**Fix:** Create PhaseTrace after all phase work is done, not before

## Pipeline Issues

### Dedup 0-groups bug (recurring)
OpenRouter/Gemini sometimes returns 0 groups from valid raw claims. The
1:1 fallback preserves data but means no dedup happened. Root cause unclear —
may be a structured output parsing issue with OpenRouter's Gemini routing.

**File:** `src/grounded_research/canonicalize.py:139-151`
**Frequency:** ~30% of runs via OpenRouter
**Fix:** Investigate whether the prompt or schema needs adjustment for OpenRouter routing. Consider a retry before falling back.

### Sub-question evidence tagging incomplete
Evidence items are tagged with `sub_question_id` based on which search query
found them. But `_select_diverse()` round-robins across queries, and the
tag only comes from the first query that found a URL. If a source was found
by multiple sub-question queries, only the first tag survives. This causes
sub-questions to show 0 evidence even when relevant evidence exists.

**File:** `src/grounded_research/collect.py:235-250`
**Observed:** LLM SWE question had 3 sub-questions with 0 evidence despite 94 total items
**Fix:** Tag evidence by checking content relevance against sub-questions (LLM call), not just search query origin
