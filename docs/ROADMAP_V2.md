# grounded-research v2 Roadmap

**Status:** Planning
**Purpose:** Prioritized feature roadmap from v1 scorecard gap analysis.
**Source:** `v1_Pruning_Scorecard.xlsx`, `docs/FEATURE_STATUS.md`, `docs/COMPETITIVE_ANALYSIS.md`

## Current State (v0.1.0)

22/34 scorecard features implemented. Pipeline beats GPT-Researcher (24 vs 15),
matches Perplexity deep research on judge verdict (21 vs 23 raw). Cost: $0.06/run.

Remaining gaps cluster into 5 themes, prioritized by competitive impact.

## Phases

Phases are sequenced by dependency and impact. Each phase has a gate — the
condition that must be met before moving to the next. Detailed plan docs and
notebooks are written at gate-time, not upfront.

### Phase A: Question Decomposition (scorecard #1, #2, #4, #5)

**Why first:** This is the #1 competitive gap. Perplexity's hidden planning
system decomposes questions before searching. We send the monolithic question
to search and analysts. Decomposition would:
- Focus evidence collection per sub-question (more relevant sources per facet)
- Give analysts structured dimensions to address (not just "analyze everything")
- Provide synthesis with explicit axes for the "key distinctions" structure

**What to build:**
- LLM call: question → `QuestionDecomposition` (precise core question, 2-6
  typed sub-questions, optimization axes, research plan with falsification targets)
- Sub-questions drive search query generation (per sub-question, not per question)
- Sub-questions passed to analysts as structured context
- Pydantic schema: `QuestionDecomposition`, `SubQuestion(text, type, falsification_target)`

**Gate:** Pipeline run on EU sanctions question with decomposition produces
typed sub-questions that visibly improve evidence coverage vs v1 (measured
by fair judge comparison).

**Acceptance criteria:**
- Sub-questions are typed (factual, causal, comparative, evaluative)
- Each sub-question gets dedicated search queries
- Analysts reference sub-questions in their analysis
- Evidence coverage score improves (completeness dimension ≥ 5 vs Perplexity)

**Scorecard items:** #1 (restate query), #2 (sub-questions), #4 (tradeoff axes),
#5 (research plan with falsification)

---

### Phase B: Source Quality & Evidence Intelligence (scorecard #15, #18, #19)

**Why second:** With 50 sources, not all are equal. Defaulting everything to
"reliable" loses signal. Source quality scoring would let synthesis weight
authoritative sources higher, and evidence sufficiency checking would flag
when sub-questions lack coverage.

**What to build:**
- LLM-based source quality scoring (per Brian's scorecard critique: LLM, not
  hardcoded URL lookup). Run after fetch, before analyst phase.
- Per-sub-question evidence sufficiency check (requires Phase A sub-questions)
- Conflict-aware compression: when context is large, preserve conflicting
  evidence and drop redundant supporting evidence

**Gate:** Source quality scores correlate with judge's "differentiate source
quality" rating. Evidence sufficiency flags correctly identify gaps.

**Acceptance criteria:**
- Each source gets a quality tier from LLM (authoritative / reliable / unknown / unreliable)
- Quality tiers visible in analyst context and synthesis
- Sub-questions with < 2 sources flagged as gaps
- Compression preserves conflicting evidence preferentially

**Scorecard items:** #15 (source scoring), #18 (conflict-aware compression),
#19 (evidence sufficiency)

**Depends on:** Phase A (sub-questions needed for per-sub-question sufficiency)

---

### Phase C: Model Resilience (scorecard #50, #51)

**Why third:** Reliability. Currently if DeepSeek or GPT-5-nano is down, we
lose an analyst entirely. Fallback chains would make the pipeline production-ready.

**What to build:**
- Per-stage fallback model config (analyst: primary → fallback → fallback2)
- llm_client already has retry logic; this adds model-level fallback
- Minimum-model thresholds already exist (#51 done); this adds graceful degradation

**Gate:** Pipeline completes successfully when one analyst model is intentionally
unavailable (simulated by using an invalid model name).

**Acceptance criteria:**
- Config specifies fallback chain per analyst slot
- Failed analyst triggers fallback model, not pipeline abort
- Fallback logged in trace with warning
- Pipeline still produces valid output with 2/3 primary models

**Scorecard items:** #50 (fallback chains), builds on #51 (thresholds, done)

**Depends on:** Nothing. Can be done in parallel with A or B.

---

### Phase D: User Steering (scorecard #40, #41)

**Why fourth:** Currently the pipeline is fully autonomous. For preference
and ambiguity disputes that can't be resolved with evidence, user input
would improve output quality. But this requires an interactive runtime
which is a bigger change.

**What to build:**
- After dispute classification, check for unresolved preference/ambiguity disputes
- If found, emit structured question(s) with sensible defaults
- CLI: prompt user, accept input or default, continue
- MCP/API: emit questions as structured output, accept answers as input

**Gate:** Pipeline pauses on a preference dispute, asks a structured question,
incorporates the answer into synthesis.

**Acceptance criteria:**
- Preference disputes detected and surfaced
- Max 2 questions per run, with defaults that allow unattended operation
- User answer recorded in trace
- Synthesis incorporates user guidance

**Scorecard items:** #40 (detect preference disputes), #41 (structured questions)

**Depends on:** Nothing architecturally, but lower priority than A-C.

---

### Phase E: Quality Polish (scorecard #25, #42, #44 and competitive analysis)

**Why last:** Incremental improvements to synthesis quality. Important but not
architectural. Should be informed by results from Phases A-D.

**What to build:**
- Enforce counter-argument requirement in analyst schema (not just prompt)
- Token-aware context compaction (tiktoken) with priority truncation
- Dispute-type-aware synthesis routing (different prompt paths for factual
  vs interpretive vs preference disputes)
- Query-type detection (from competitive analysis: academic vs news vs
  policy routes to different report structures)

**Gate:** Fair comparison score vs Perplexity deep research improves to
≥ 23/25 (currently 21/25).

**Scorecard items:** #25 (counter-argument), #42 (compaction), #44 (synthesis routing)

**Depends on:** Phases A and B (needs sub-questions and quality scores in context).

---

## Phase Sequencing

```
Phase A (decomposition) ──→ Phase B (source quality) ──→ Phase E (polish)
                                                              ↑
Phase C (model resilience) ─────────────────────────────────┘
                                                              ↑
Phase D (user steering) ────────────────────────────────────┘
```

A → B → E is the critical path (competitive gap).
C and D are independent and can be done in parallel at any time.

## Notebook Plan

Per CLAUDE.md rule #10: "Concretize contracts in a notebook BEFORE implementing."

| Phase | Notebook | When to write |
|-------|----------|---------------|
| A | `docs/notebooks/02_question_decomposition.ipynb` | Before implementing Phase A |
| B | `docs/notebooks/03_source_quality.ipynb` | After Phase A gate passes |
| C | No notebook needed (config + simple fallback logic) | — |
| D | `docs/notebooks/04_user_steering.ipynb` | After Phase B gate passes |
| E | No separate notebook (improvements to existing pipeline) | — |

## Deferred Features (from scorecard)

These remain deferred until evidence shows they're needed:

| # | Feature | Why deferred |
|---|---------|-------------|
| 8-12 | Decomposition validation | Frontier models decompose well enough for v2 |
| 14 | Grok/Reddit real-time scan | Third API integration for marginal value |
| 17 | Echo detection | Rarely enough near-duplicates to justify |
| 30 | Evidence-label leakage check | Careful reader can see sources in trail |
| 43 | Self-preference bias guard | Tested with 2 judges, no bias detected |

## Open Questions (decide at phase gate time)

1. **Decomposition model**: Use the synthesis model (gemini-2.5-flash) or a
   dedicated planning model? Planning needs reasoning, not generation.
2. **Source quality persistence**: Score per-run or build toward persistent
   source reputation DB? (deferred idea in `PROJECTS_DEFERRED/source_reputation_db.md`)
3. **User steering UX**: CLI-only or also MCP tool surface?
4. **Compaction strategy**: Token-count truncation or LLM-based summarization?
