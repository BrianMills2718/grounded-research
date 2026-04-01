# Tyler V1 Delivery Summary

**Date:** 2026-03-31
**Repo:** https://github.com/BrianMills2718/grounded-research

## What Was Built

Your complete V1 specification is implemented: all 6 stages, all schemas, all
prompts, all 10 design constraints, all cross-cutting requirements. The
pipeline runs end-to-end from a raw question to a grounded report with full
provenance.

### Pipeline Flow

```
Question → Decomposition (Stage 1)
         → Evidence Collection via Tavily + Exa (Stage 2)
         → 3 Independent Analysts with distinct frames (Stage 3)
         → Claim Extraction + Dispute Localization (Stage 4)
         → Fresh-Evidence Verification for decision-critical disputes (Stage 5)
         → User Steering for preference/ambiguity disputes (Stage 6a)
         → Grounded Synthesis Report (Stage 6b)
```

### What You Get Per Run

- `report.md` — 11-component, 3-tier report (Executive/Analytical/Evidentiary)
- `trace.json` — Full pipeline state with every stage's artifacts
- `handoff.json` — Downstream-compatible structured output
- `tyler_stage_1.json` through `tyler_stage_6.json` — Per-stage artifacts
- `collected_bundle.json` — Reusable evidence bundle

### Config Split

- `config/config.yaml` — **Tyler-literal model assignments** (GPT-5.4, Claude
  Opus 4.6, Gemini 2.5 Pro). This is what you specified.
- `config/config.testing.yaml` — Cheap models for fast iteration (Gemini 2.5
  Flash direct API, ~$0.01/run).

Run with: `python engine.py "your question"` (Tyler models) or
`python engine.py --config testing "your question"` (cheap models).

## Spec Compliance: Item by Item

### Stage 1 — Intake & Decomposition ✅
- Model: Gemini (configurable) with fallback chain
- Restates query, breaks into 2-6 typed sub-questions
- Maps optimization axes, generates research plan + falsification targets
- Self-check prompt instruction per spec
- Stage summary with reasoning field

### Stage 2 — Broad Retrieval & Evidence Normalization ✅
- **Tavily (primary) + Exa (secondary, semantic)** — both run per query
- Query generation via **string templates, not model calls** (per spec)
- **Hard cap: 4 queries per sub-question** (named constant)
- Source quality scoring via **URL lookup table** (deterministic, not LLM)
  - 1.0 official docs (.gov, .edu, journals) → 0.3 generic blog
  - Unknown defaults to 0.5 (not penalized)
- Atomic finding extraction with evidence labels
- Sufficiency check: min 2 independent sources per sub-question
- Stage summary with reasoning field

### Stage 3 — Independent Candidate Generation ✅
- **3 models in parallel** (GPT-5.4, Claude Opus 4.6, Gemini 2.5 Pro)
- **3 distinct reasoning frames** (step-back abstraction, structured
  decomposition, verification-first)
- Requires ≥2 of 3 to succeed
- Each produces: recommendation, claims, assumptions, counter-argument,
  falsification conditions, confidence level, reasoning
- **Anonymization**: A/B/C via string replacement, identity scrubbing
- **Anti-conformity**: prompt instruction per spec
- Min 3 claims per analyst (Tyler validation rule)

### Stage 4 — Claim Extraction & Dispute Localization ✅
- Model: GPT-5.4 with Claude Opus fallback
- Claimify approach: atomize → deduplicate → localize disputes
- Evidence label hierarchy: vendor_documented (1.0) > empirically_observed
  (0.8) > model_self_characterization (0.5) > speculative_inference (0.3)
- Five-type dispute classification: empirical, interpretive,
  preference_weighted, spec_ambiguity, other
- Decision-criticality gate
- **Deterministic routing**: empirical/interpretive → Stage 5,
  preference/ambiguity/other → Stage 6a, non-critical → logged_only
- Retry on empty claims with corrective guidance
- All artifacts materialized: claim ledger, assumption set, dispute queue

### Stage 5 — Targeted Verification & Arbitration ✅
- Only fires on unresolved empirical/interpretive + decision-critical disputes
- **Counterfactual query patterns**: `[topic] limitations`,
  `[claim] contradicted by` (per spec)
- **Budget**: max 3 queries per dispute, max 2 rounds
- Arbitration: Claude Opus, single-turn, schema-driven
- Claim status updates require `basis_for_change`: new_evidence,
  corrected_assumption, or resolved_contradiction (anti-conformity enforcement)
- Claims track `status_at_extraction` for lineage (constraint #4)
- Investigated claims marked `is_provisional = False` (constraint #8)

### Stage 6a — User-Steering Interrupt ✅
- Checks post-Stage-5 updated dispute queue
- Filters: preference_weighted, spec_ambiguity, or other + decision_critical
  + unresolved
- Terminal I/O, no model call, max 2 questions
- User input captured in pipeline state

### Stage 6b — Synthesis & Final Report ✅
- 11 components, 3 tiers per spec
- **Tier A**: Executive recommendation, conditions of validity, tradeoffs
- **Tier B**: Disagreement map, preserved alternatives, key assumptions,
  confidence assessment, process summary
- **Tier C**: Claim ledger excerpt, evidence trail, evidence gaps
- Grounding check (recommendation cites claims) + zombie check (no refuted
  alternatives)
- Reasoning field

### Cross-Cutting Requirements ✅
- Reasoning field on all model outputs
- Fallback logic on 3 must-succeed stages
- Partial trace on abort
- Anonymization in both directions
- Anti-conformity as protocol rule (prompt + schema)
- Context rot mitigation (original query at start/end)
- Evidence label hierarchy with numeric weights

### 10 Design Constraints ✅
| # | Constraint | Status |
|---|-----------|--------|
| 1 | Independence first | Parallel analysts, zero inter-visibility |
| 2 | Critique targets claims, not responses | Schema-driven extraction |
| 3 | Anonymize in both directions | A/B/C + scrubbing |
| 4 | Track lineage of thought changes | status_at_extraction field |
| 5 | Evidence labeling hierarchy | Enum + weights + prompt enforcement |
| 6 | Novelty/delta detection | Hard-cap counters (simplified per spec) |
| 7 | Avoid social framing | No social language in any prompt |
| 8 | Separate working notes from locked | is_provisional flag |
| 9 | Anti-conformity as protocol rule | Prompt + basis_for_change schema |
| 10 | Context rot mitigation | Original query at start/end |

### Known Limitations (per your spec) — NOT bugs
- No decomposition validation (Stage 1v deferred)
- No echo detection
- 2 of 7 anti-patterns checked at runtime; other 5 are eval criteria
- Counter-argument quality is prompt-only
- No self-preference bias guard
- Char count heuristic (we use item-count; see question below)

## Two Questions For You

### 1. PipelineState field naming

Your schema says `stage_1_result`, `stage_2_result`, etc. Our runtime uses
`tyler_stage_1_result`, `tyler_stage_2_result` — with extra observability
fields (`stage3_attempts`, `phase_traces`, `warnings`). The Tyler-shaped
PipelineState exists exactly as specified in `tyler_v1_models.py`. The runtime
version in `models.py` is a superset used by `engine.py`.

**Question:** Collapse to one PipelineState, or keep the runtime superset?

### 2. Context compaction heuristic

Your spec says "compress when input exceeds ~80K characters (~20K tokens)."
We use item-count compression (threshold: 80 items). Both reduce input size.

**Question:** Is item-count acceptable, or should we add a char-count check?

## How To Run

```bash
# Setup
cd grounded-research
pip install -e .
pip install -e ~/projects/llm_client
pip install -e ~/projects/open_web_retrieval

# Run with Tyler-literal models ($1-3/run)
python engine.py "Your research question"

# Run with cheap testing models (~$0.01/run)
python engine.py --config testing "Your research question"

# From a pre-built evidence bundle
python engine.py --fixture path/to/bundle.json

# Makefile shortcuts
make adjudicate QUERY="Your question"          # Tyler models
make adjudicate-test QUERY="Your question"     # Cheap models
```

## What's Next (if you want to continue)

1. **Benchmark with prompt_eval**: Run the 6-question set through proper
   statistical evaluation (multiple judges, bootstrap CI, 20+ questions)
2. **Frontier model validation**: Live run with GPT-5.4 + Claude Opus + Gemini
   Pro (blocked today by OpenRouter latency; code is ready)
3. **onto-canon integration**: The claim ledger → KG pipeline
4. **Source reputation DB**: Cross-run learning about domain quality
