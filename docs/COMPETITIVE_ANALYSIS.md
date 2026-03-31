# Competitive Analysis: grounded-research vs Perplexity Deep Research

**Last updated:** 2026-03-31

## Current Benchmark (6-question set, GPT-5-nano judge, blind evaluation)

| Question | Domain | Pipeline | Perplexity | Winner |
|----------|--------|----------|------------|--------|
| EU sanctions | Policy | **23** | 22 | **Pipeline** |
| PFAS | Health/Regulatory | **24** | 20 | **Pipeline** |
| Fasting | Health/Science | **24** | 22 | **Pipeline** |
| LLM SWE | Technology | **24** | 20 | **Pipeline** |
| UBI | Economics | **24** | 22 | **Pipeline** |
| Gut-brain | Science | **20** | 18 | **Pipeline** |

**Win rate: 6/6 (100%).** Average: 23.2/25 vs 20.7/25.

**Methodology:** 5 dimensions (Factual Accuracy, Completeness, Conflict/Nuance,
Analytical Depth, Decision Usefulness), each scored 1-5. GPT-5-nano as blind
judge. Perplexity outputs are cached from the original comparison date, not
re-run. Pipeline cost: ~$0.06/run (standard depth).

**Caveats:**
- 6 questions is too few for statistical significance
- Single LLM judge (known bias toward structured output)
- Cached Perplexity comparisons, not live re-runs
- Same team built and evaluated

## Where Pipeline Wins

1. **Decision usefulness** — Structured alternatives with "when to choose this
   option" conditions. Perplexity describes options but doesn't structure them
   as decision rules.
2. **Conflict/nuance** — Explicit dispute detection and resolution with
   arbitration trail. Perplexity acknowledges disagreements but doesn't resolve
   them with fresh evidence.
3. **Claim-level provenance** — Every assertion traces to evidence through a
   typed claim ledger. Unique structural asset.
4. **Explicit uncertainty** — "What the Evidence Doesn't Tell Us" with concrete
   gaps and testable conditions for re-evaluation.

## Where Pipeline Loses

1. **Specific quantitative data** — Perplexity cites "meta-analysis of 99 RCTs",
   "NBER study N=1,000." Pipeline produces "studies show weight loss of 3-8%."
2. **Breadth of examples** — Perplexity lists 8-12 specific programs by name.
   Pipeline discusses 3-5 in less detail.
3. **Macro-economic connections** — Perplexity connects findings to GDP, budget
   deficits, labor markets. Pipeline stays closer to the direct question.
4. **Population-specific detail** — "For pregnant women...", "In the Finnish
   context..." vs general "vulnerable populations."

See `docs/JUDGE_CRITIQUES.md` for the detailed weakness analysis.

## Benchmark History

The pipeline improved from 4/6 to 6/6 over a 5-day calibration period:

| Date | Win Rate | Key Change |
|------|----------|------------|
| 2026-03-23 | 2/3 | Initial 3-question test |
| 2026-03-24 | 4/6 | Full 6-question set; lost LLM SWE + UBI |
| 2026-03-24 | 5/6 | Bug fixes (ID override, dedup, evidence tagging) recovered LLM SWE |
| 2026-03-26 | 6/6 | Dense-dedup hardening + report calibration recovered UBI |

The EU sanctions question progressed from 20/25 (v3) to 23/25 (v10) — the
single biggest improvement was switching to analytical synthesis mode.

## Comparison Architecture

**Perplexity** uses a two-system architecture:
1. Planning system (hidden): search strategy, query issuing, URL navigation
2. Synthesis system (prompt available): formatting-focused, no hedging, citation
   discipline

**grounded-research** uses a 6-stage pipeline:
1. Decomposition → 2. Collection (Tavily+Exa) → 3. Independent analysts (3
   models, 3 frames) → 4. Claim extraction + dispute detection → 5. Fresh
   evidence arbitration → 6. Grounded synthesis

The key difference: Perplexity's depth comes from broader search. Ours comes
from structured disagreement resolution.

## What We Learned From Perplexity

- Query-type routing (different questions need different report structures)
- Summary sandwich (begin and end with summary)
- Citation discipline (max 3 sources per sentence)
- Their "no hedging" ban trades accuracy for confidence — our explicit
  uncertainty sections are an advantage, not a flaw

## Next Benchmark Steps

- Run through `prompt_eval` with multiple judge models and 20+ questions
- Add dimensional scoring with bootstrap CI for statistical significance
- Compare against live Perplexity output, not cached
