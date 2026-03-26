# Judge Critiques: Historical Losses And Residual Weaknesses

This document preserves the recurring weaknesses extracted from earlier blind
judge evaluations against Perplexity deep research.

The tracked benchmark state later improved to a calibrated 6/6 win set, but the
themes below still matter as residual quality risks, especially on
enumeration-heavy questions.

## Recurring Weaknesses (pipeline scores 4 where Perplexity scores 5)

### 1. Specific quantitative data from named studies
**Frequency:** 5/6 questions
**What Perplexity does:** "a meta-analysis of 99 RCTs", "NBER study N=1,000, $1,000/month for 3 years", "60.4% SWE-bench Verified resolution"
**What pipeline does:** "studies show weight loss of 3-8%", "pilot programs generally show minimal effects"
**Root cause:** Analysts produce abstract claims, not study-level citations. The quantitative claims fix helped but isn't sufficient — we need study names, sample sizes, and specific effect sizes consistently.
**Fix:** Analyst prompt needs stronger instruction: "Name specific studies, their sample sizes, and exact findings."

### 2. Breadth of specific examples/programs/benchmarks
**Frequency:** 4/6 questions (UBI, LLM SWE, sanctions, fasting)
**What Perplexity does:** Lists 8-12 specific pilot programs by name, location, and duration. Enumerates 6+ specific benchmarks with scores.
**What pipeline does:** Discusses 3-5 examples in less detail.
**Root cause:** 50 sources with ~80 evidence items after compression. Perplexity uses 50 sources too but their search finds more diverse specific examples.
**Fix:** Search queries should explicitly target "list of X programs/studies/benchmarks" for enumeration-heavy questions.

### 3. Macro-economic and second-order implications
**Frequency:** 3/6 questions (sanctions, UBI, fasting)
**What Perplexity does:** Connects findings to budget deficits, GDP growth, fiscal policy, labor market structure
**What pipeline does:** Stays closer to the direct question with a "Broader Implications" section that's often thin
**Root cause:** The analytical mode helps but the long_report prompt's "Broader implications" section instruction is vague
**Fix:** Strengthen the broader implications prompt: "Connect findings to macro-economic effects, institutional changes, and second-order consequences. Be specific — name which budgets, which policies, which institutions are affected."

### 4. Population/subgroup-specific detail
**Frequency:** 2/6 questions (fasting, UBI)
**What Perplexity does:** "For pregnant women...", "For people with type 2 diabetes...", "In the Finnish context..."
**What pipeline does:** General claims about "vulnerable populations" without specifics
**Root cause:** Analyst prompt was improved (#5 in the analyst instructions) but still produces general claims
**Fix:** Already addressed — may need stronger reinforcement in the prompt

## Where Pipeline Consistently Wins

### Decision usefulness (5/5 on 5/6 questions)
Structured alternatives with "when to choose" conditions and "what would change this recommendation" — Perplexity can't do this because it doesn't have a claim ledger to reason over.

### Conflict/nuance (5/5 on 3/6 questions)
Explicit dispute detection and resolution with arbitration trail. Perplexity acknowledges disagreements but doesn't resolve them with fresh evidence.

## Priority Improvements (ordered by expected impact)

1. **Study-level specificity in analyst claims** — the single biggest gap
2. **Enumeration-targeted search queries** — for benchmark/program-heavy topics
3. **Stronger broader implications prompt** — specific macro connections
4. **Population-specific detail reinforcement** — already partially addressed
