# Competitive Analysis: grounded-research vs SOTA

**Date:** 2026-03-23
**Question tested:** EU sanctions on Russia (effectiveness on oil/gas revenue)

## Tools Compared

| Tool | Approach | Sources | Words | Cost | Time |
|------|----------|---------|-------|------|------|
| **grounded-research v4** | 3 cross-family analysts + arbitration + synthesis | 50 | 3,891 | $0.07 | ~3 min |
| **Perplexity deep research** | Planning system + search + synthesis | 50 | 6,451 | ~$0.05 | 155s |
| **GPT-Researcher** | Auto-search + single synthesis | ~10 | 1,560 | $0.025 | 61s |
| **STORM (Stanford)** | Multi-perspective conversation + synthesis | — | — | — | Failed |

## Fair Comparison Results (GPT-5-nano judge, no provenance bias)

5 dimensions: Factual Accuracy, Completeness, Conflict/Nuance, Analytical Depth, Decision Usefulness.

### grounded-research vs GPT-Researcher

| Dimension | grounded-research | GPT-Researcher |
|-----------|------------------|----------------|
| Factual Accuracy | 4 | 3 |
| Completeness | 5 | 3 |
| Conflict & Nuance | 5 | 3 |
| Analytical Depth | 5 | 3 |
| Decision Usefulness | 5 | 3 |
| **Total** | **24** | **15** |

Length-normalized (1,900 vs 1,560 words): 21 vs 17. Pipeline wins at any length.

### grounded-research vs Perplexity deep (20 sources)

| Dimension | grounded-research | Perplexity |
|-----------|------------------|------------|
| Factual Accuracy | 4 | 4 |
| Completeness | 4 | 5 |
| Conflict & Nuance | 4 | 5 |
| Analytical Depth | 4 | 5 |
| Decision Usefulness | 4 | 5 |
| **Total** | **20** | **24** |

### grounded-research vs Perplexity deep (50 sources)

| Dimension | grounded-research | Perplexity |
|-----------|------------------|------------|
| Factual Accuracy | 4 | 4 |
| Completeness | 4 | 5 |
| Conflict & Nuance | 4 | 5 |
| Analytical Depth | 4 | 5 |
| Decision Usefulness | 5 | 4 |
| **Total** | **21** | **23** |

## What Perplexity Does Better

1. **Broader macro-economic integration** — connects sanctions to Russia's
   budget deficits, GDP growth, fiscal policy, and strategic shifts. Our
   pipeline stays closer to the direct sanctions→revenue chain.

2. **Explicit analyst disagreements** — surfaces competing views among
   researchers and policymakers on optimal approach. Our pipeline detects
   disputes between its own analysts but doesn't surface third-party debate.

3. **Political feasibility constraints** — notes Hungary blocking the 20th
   package, coalition dynamics. Our pipeline treats sanctions as policy
   facts, not as political negotiations.

4. **Quantitative causal decomposition** — separates revenue decline from
   pricing effects vs volume effects. Our pipeline reports aggregate impacts.

## What grounded-research Does Better

1. **Structured decision framework** — explicit policy alternatives with
   conditional triggers ("when to choose this option"). Perplexity describes
   options but doesn't structure them as decision rules.

2. **Explicit uncertainty sections** — "What the Evidence Doesn't Tell Us"
   with concrete gaps and testable conditions for re-evaluation. Perplexity's
   prompt explicitly bans hedging language.

3. **Claim-level provenance** — every assertion traces to specific evidence
   through a typed claim ledger. Not captured in prose comparison but is the
   unique structural asset.

4. **Fresh evidence arbitration** — resolves factual conflicts by fetching
   new evidence. No other tool does this.

## Perplexity Architecture (from leaked prompt)

Perplexity uses a two-system architecture:
1. **Planning system** (not visible): Decides search strategy, issues queries,
   navigates URLs, explains reasoning. This is where the analytical depth
   comes from.
2. **Synthesis system** (prompt available): Formats the planning system's
   findings into a polished report. The prompt is almost entirely about
   formatting — markdown rules, citation style, list vs table, no hedging.

Key design choices in the synthesis prompt:
- **No hedging language** — "NEVER use moralization or hedging language"
- **Begin and end with summary** — sandwich structure for readability
- **Cite up to 3 sources per sentence** — prevents citation clutter
- **Query type routing** — academic research gets long/detailed, news gets
  concise, weather gets short. Different question types → different formats.
- **Journalistic tone** — "unbiased and journalistic tone" throughout

### What we can learn

1. **Query-type routing**: We should detect question type and adjust report
   structure. A factual policy question needs different treatment than a
   technology comparison or health risk assessment.

2. **Formatting precision**: Their markdown rules are much more specific than
   ours. Tables for comparisons, flat lists only, no mixed list types.

3. **Summary sandwich**: Begin with summary, end with summary. Good for
   readability — our reports jump straight into analysis.

4. **Citation discipline**: "Cite up to three relevant sources per sentence"
   prevents the citation clutter our reports sometimes have.

5. **Their planning system is the real advantage** — the synthesis prompt is
   a formatter. Their search/reasoning system (which we don't see) is what
   produces the analytical depth. Our equivalent is the multi-analyst loop,
   which works differently but serves the same purpose.

### What NOT to copy

1. **No hedging** — their ban on uncertainty language is a readability choice
   that trades accuracy for confidence. Our explicit uncertainty sections are
   a genuine analytical advantage, not a flaw to fix.

2. **Single-pass synthesis** — they don't have dispute detection or
   arbitration. Their depth comes from broader search, not from structured
   disagreement resolution.

## Closing the Gap

The 2-point gap (21 vs 23) with 50 sources comes from synthesis quality,
not evidence breadth. Specific improvements:

1. **Broader analytical frame** — prompt the long report to explicitly
   connect findings to macro-economic context, political feasibility, and
   strategic implications (not just direct policy effects).

2. **Third-party disagreements** — during analysis, ask analysts to identify
   not just evidence conflicts but also known expert/institutional debates
   on the topic.

3. **Causal decomposition** — ask analysts to separate effects by mechanism
   (pricing vs volume, direct vs indirect, short-term vs structural).

4. **Summary sandwich** — add opening and closing summaries to long report.

5. **Query-type detection** — route different question types to different
   report structures.
