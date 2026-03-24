# Plan: Configurable Research Depth

**Status:** Planned
**Priority:** High — directly addresses the #1 competitive gap

## Problem

The pipeline runs at one fixed depth. For enumeration-heavy topics (UBI
with 20+ pilot programs), this isn't enough. Perplexity wins because it
searches more broadly and extracts more specific details per source.

Brian's feedback: "this is meant to be an expensive longer running more
heavily researched result."

## Design: Depth Profiles

Config key: `depth: "standard" | "deep" | "thorough"`

| Setting | standard (current) | deep | thorough |
|---------|-------------------|------|----------|
| Search queries per SQ | 3 | 5 | 8 |
| Max sources | 50 | 100 | 150 |
| Evidence items per source | 1-2 | 3-5 | 5+ |
| Compression threshold | 80 | 150 | none |
| Analyst claim target | ~8 | ~15 | ~20 |
| Arbitration rounds | 1 | 2 | 3 |
| Synthesis word target | 5,000-6,000 | 8,000-10,000 | 10,000-15,000 |
| Estimated cost | $0.06 | $0.15-0.25 | $0.50-1.00 |
| Estimated time | 3 min | 8-12 min | 20-30 min |

## Implementation

### Phase 1: Config-only changes (no new infrastructure)

These can be done immediately by adding a `depth` key that sets multiple
config values at once:

1. `config.yaml`: add `depth: "standard"` with override table
2. `config.py`: add `get_depth_config()` that returns all depth-dependent values
3. `engine.py`: read depth config, pass to collection/analysis/synthesis
4. `prompts/analyst.yaml`: add claim count target instruction
5. `prompts/long_report.yaml`: adjust word count target per depth

### Phase 2: Goal-driven evidence extraction (needs work)

Currently `fetch_page` extracts one `key_section` + one `notes` per page
using a heuristic. The extraction prompt should be goal-driven per the
prompt-design skill: tell the LLM what we need and why, not how many items.

**Approach:** Replace heuristic extraction with a YAML prompt template that
receives the research question and sub-questions as context:
"You are extracting evidence to answer a research question. This page may
contain data points, study findings, organizational positions, or
quantitative claims relevant to these sub-questions: [list]. Extract every
distinct piece of evidence that could help answer them."

**Key principle:** More sources is better than more items per source. The
primary lever is `max_sources`. The extraction improvement ensures we don't
miss important evidence on pages we already fetch.

**Where:** New prompt `prompts/extract_evidence.yaml` + function in `collect.py`
**Cost:** ~1 LLM call per source (~50-150 calls depending on depth)

### Phase 3: Multi-round arbitration (needs work)

Currently one round of search + arbitrate per dispute. For deep mode,
if the first round is inconclusive, generate new search queries targeting
the specific gap and try again.

**Where:** `verify.py`: loop in `verify_disputes()` with configurable max_rounds
**Cost:** ~2-3x current arbitration cost

### Phase 4: Sectioned synthesis (needs work, may need llm_client support)

For 10K+ word reports, a single LLM call may hit output token limits.
Options:
- (a) Use a model with higher output limits (Claude has 16K+)
- (b) Synthesize in sections: one call per key distinction, then a
  joining call for intro/verdict/closing
- (c) Two-pass: breadth pass covering all sub-questions, then depth
  pass expanding important findings

**Recommendation:** Start with (b) — sectioned synthesis. Each section
is an independent LLM call that can be long and detailed. The joining
call stitches them together.

**llm_client needed?** Only if we need to split a single structured output
across multiple calls. Otherwise, just multiple `acall_llm` calls.

## Pre-Made Decisions

1. Config key: `depth: "standard" | "deep" | "thorough"`
2. CLI flag: `--depth deep` overrides config
3. Default: `standard` (current behavior, backward compatible)
4. Deep mode: 2x sources, 3-5 evidence per source, 15 claims target, 8K words
5. Thorough mode: 3x sources, 5+ evidence per source, 20 claims target, 12K words
6. Cost budget scales with depth (deep: $0.50, thorough: $2.00)

## Acceptance Criteria

- Deep mode on UBI question scores ≥ 23/25 (currently 20)
- Thorough mode produces ≥ 10K word report with study-level detail
- Standard mode unchanged (no regression)
- Depth configurable via config.yaml and CLI flag
