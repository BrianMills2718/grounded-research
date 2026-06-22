# Grounded Research Methodology

Wiki home: http://localhost:8088/index.php/Project_Wiki

## Goal

The project goal is to make research answers grounded in a reviewable claim
ledger. The report is a rendering of structured evidence, claims, disputes,
verification results, and remaining uncertainty.

The thesis is:

- independent analysts over shared evidence expose useful disagreement;
- claims can be canonicalized and deduplicated into a ledger;
- only decision-critical disputes need fresh verification;
- unresolved disputes should remain visible instead of being smoothed into a
  confident narrative;
- every final answer should preserve its trace.

## Workflow

1. Accept either a raw question or an imported evidence bundle.
2. Decompose the question into typed sub-questions and research guidance.
3. Collect or normalize evidence with source quality and provenance.
4. Run independent analyst passes with distinct reasoning frames.
5. Extract claims and assumptions from analyst outputs.
6. Deduplicate claims into a canonical ledger.
7. Detect, classify, and route disputes.
8. Verify decision-critical factual or interpretive disputes with fresh
   evidence.
9. Surface preference or ambiguity disputes when they need user steering.
10. Synthesize a final report from the ledger, evidence, disputes, and trace.

## Design Principles

- The claim ledger is the product.
- The report must not invent structure missing from the ledger.
- Analyst passes must be independent.
- LLMs handle semantic judgment; code handles routing, IDs, validation,
  budgets, and trace serialization.
- Prompts are data in `prompts/`.
- All LLM calls go through `llm_client`.
- Search and fetch belong in shared retrieval infrastructure when possible.
- Unknown or malformed stage outputs fail loudly.

## Modality Split

Deductive / plan-first surfaces:

- Tyler stage schemas;
- Pydantic phase contracts;
- prompt templates;
- stage input/output artifacts;
- trace and handoff artifacts;
- config-controlled model and budget policy;
- fail-loud validation and grounding checks.

Exploratory / ladder surfaces:

- whether independent analysts produce useful disagreement on a new domain;
- whether fresh evidence resolves a dispute;
- whether Tyler-literal prompts outperform calibrated legacy variants;
- whether a benchmark win generalizes beyond the tracked cases;
- whether retrieval depth or source mix is the bottleneck for a specific
  question.

Exploratory surfaces require saved runs and comparison artifacts, not broader
claims in prose.

## ADR Map

Existing ADRs under [docs/adr/](adr/) cover adjudication scope, external reuse,
fallback/fetch strategy, agentic verification, cross-family model frames, and
decomposition decisions.

This dossier adds no new runtime ADR. It summarizes the existing methodology
for wiki navigation.

## Main Failure Modes

| Failure mode | Why it matters | Control |
|---|---|---|
| Treating the report as the source of truth | Prose can hide unsupported synthesis. | Treat `trace.json` and the claim ledger as canonical. |
| Analyst convergence masquerading as evidence | Multiple LLMs can repeat the same weak frame. | Preserve independent frames and inspect disagreement quality. |
| Overgeneralizing benchmark wins | Tracked cases do not prove broad superiority. | State dataset, judge, comparison target, and scope. |
| Retrieval novelty displacing adjudication thesis | The project value is not generic search. | Keep adjudication and claim-ledger evidence central. |
| Tyler compliance drift | Local docs can outrun code/spec reality. | Use `docs/TYLER_SPEC_GAP_LEDGER.md` as the truth surface. |

