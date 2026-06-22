# Grounded Research Project Dossier

Wiki home: http://localhost:8088/index.php/Project_Wiki

## Portfolio Role

Grounded Research is a core analyst-methods and AI-engineering project. It is
best presented as an adjudication-centered research system: a question is
decomposed, evidence is collected or imported, independent analyst passes
produce claims, disagreements are localized, decision-critical disputes are
verified with fresh evidence, and the final report renders a traceable claim
ledger.

The strongest portfolio claim is not that this is another research chatbot. The
stronger claim is that a research system can make disagreement, uncertainty,
and provenance first-class artifacts.

## Current Status

The live repo is Tyler-native on the Stage 1-6 runtime path and has a substantial
audit trail around Tyler V1 compliance. The README reports benchmark wins
against cached Perplexity Deep Research on the tracked six-question set and a
Tyler-native UBI case. Treat those as tracked evaluation artifacts, not a
general claim that the system beats all research agents on all tasks.

Safe current claims:

- raw-question and imported-evidence entry modes;
- question decomposition into typed research tasks;
- multi-analyst reasoning over shared evidence;
- claim extraction, semantic deduplication, and dispute classification;
- decision-critical dispute verification with fresh evidence;
- Tyler-native trace and handoff artifacts;
- provenance from report back to claim ledger, analyst, evidence, and source;
- documented code-vs-spec gap ledger and audit governance.

Do not claim:

- complete general-purpose research-agent superiority;
- universal benchmark leadership;
- fully solved retrieval;
- absence of hallucination or unsupported claims;
- all Tyler packet ambiguities are resolved by the upstream spec;
- every source-quality or dispute-resolution decision is methodologically
  validated beyond the tracked artifacts.

## Reviewer Path

1. Read [docs/ADJUDICATION_WALKTHROUGH.md](docs/ADJUDICATION_WALKTHROUGH.md)
   for the short portfolio story.
2. Read [docs/METHODOLOGY.md](docs/METHODOLOGY.md) for the adjudication method.
3. Read [docs/ARCHITECTURE_ONE_PAGE.md](docs/ARCHITECTURE_ONE_PAGE.md) for
   architecture boundaries.
4. Read [docs/CONTRACTS.md](docs/CONTRACTS.md) and
   [docs/DOMAIN_MODEL.md](docs/DOMAIN_MODEL.md) for typed artifacts and
   stage contracts.
5. Read [docs/VALIDATION.md](docs/VALIDATION.md) before repeating benchmark or
   Tyler-compliance claims.
6. Read [docs/ARTIFACTS.md](docs/ARTIFACTS.md) and
   [docs/CONCERNS.md](docs/CONCERNS.md) for evidence and remaining risks.

## Why It Matters For An AI Engineer / Analyst Portfolio

This project is a strong bridge between AI engineering and analyst tradecraft.
It demonstrates typed stage contracts, structured LLM calls, shared evidence
handling, independent analyst frames, dispute routing, fresh-evidence
verification, provenance-rich traces, and rigorous audit documentation.

For an intelligence-analysis portfolio, the project shows that the system is
designed around disagreement and evidence, not only answer generation.

## Next Evidence To Create

The next high-value portfolio work is a compact public reviewer packet:

1. One non-sensitive question with saved input, evidence bundle, trace, report,
   and handoff artifacts.
2. A short source-to-claim walkthrough showing a final report claim traced back
   to the ledger and evidence.
3. A benchmark note explaining exactly what comparison was run and what it does
   not generalize to.
4. A caveat table separating Tyler-literal compliance, tracked benchmark wins,
   and future evaluation needs.

