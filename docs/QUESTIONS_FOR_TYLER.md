# Questions for Tyler: Implementation-Blocking Decisions

This doc asks only the questions that change code paths, contracts, or
acceptance criteria. It does not ask for production model picks, cost ceilings,
or other config values. Those can be shipped later as `config` changes.

**Current assumption:** development keeps using cheap models so iteration stays
fast. Production model selection is a separate config concern and does not block
implementation.

**How to respond:** For each question, either say `use default` or give a
concrete rule we can encode in code, schemas, prompts, tests, or docs.

---

## 1. Product Boundary

**Why this matters:** The repo currently says two different things.
`README.md` presents a full question-to-report research system. `CLAUDE.md`
still says v1 is an adjudication-first layer over shared evidence. This changes
what the benchmark is, what docs should promise, and which failure modes matter.

**Question:** What is the intended v1 product boundary?

- Option A: Adjudication-first system. Cold-start retrieval stays available, but
  the thesis and benchmark focus on multi-analyst disagreement over shared
  evidence.
- Option B: Full end-to-end research system. Retrieval, decomposition,
  adjudication, and synthesis are all part of the product thesis.
- Option C: Hybrid. End-to-end flow is supported, but success is judged
  primarily on contested questions where adjudication adds value.

**Default:** Option C.

---

## 2. Claim Contract

**Why this matters:** "Be more specific" is not a contract. Before adding claim
validators or retries, we need to know what a valid claim must contain and what
should happen when the source does not support that level of specificity.

**Question:** What must a claim include to be accepted into the ledger?

Please answer in this shape:

- Always required:
- Required when available in the source:
- Acceptable fallback when specificity is impossible:
- Failure behavior: retry, drop, or mark low-specificity

**Default:**

- Always required: self-contained statement, direction/polarity, evidence IDs
- Required when available in the source: source/study name, timeframe, and at
  least one concrete detail such as a number, population, or measured outcome
- Acceptable fallback when specificity is impossible: keep the claim but mark it
  `low_specificity` in structured state
- Failure behavior: one retry with source excerpts, then keep only if marked
  `low_specificity`

---

## 3. Ambiguity And User Interrupt Policy

**Why this matters:** There are two materially different designs:

- detect ambiguity early and ask before retrieval
- let the pipeline continue, then surface unresolved ambiguity later

This changes control flow, user experience, and wasted work.

**Question:** When should the system interrupt the user?

- Option A: Before retrieval, when ambiguity would materially change the search
  plan or recommendation
- Option B: Only after dispute detection, as the current late-stage interrupt
- Option C: Never interrupt; always surface alternatives in the report
- Option D: Mixed policy. Specify exactly which cases interrupt early and which
  are only surfaced later

**Default:** Option D. Interrupt early for material spec ambiguity that would
change retrieval or ranking. Keep the current late-stage interrupt for
preference/ambiguity disputes discovered downstream. Max 2 questions.

---

## 4. Anti-Conformity Enforcement Contract

**Why this matters:** "Only change position with new evidence, corrected
assumption, or resolved contradiction" needs a code-level rule. Otherwise the
system only gestures at rigor.

**Question:** What must be true before a claim update is accepted?

Please answer in this shape:

- Allowed basis for changing a claim:
- Evidence/justification fields the schema must carry:
- Validator behavior on failure:
- Should failed validation be a hard gate or only a warning?

**Default:**

- Allowed basis: `new_evidence`, `corrected_assumption`, or
  `resolved_contradiction`
- Schema must carry: `basis_type`, cited evidence IDs, and short textual
  justification tied to the cited evidence
- Validator behavior on failure: reject that claim update and record a warning
  in trace state
- Enforcement level: hard gate per `claim_update`

---

## 5. Analyst Diversity Mechanism

**Why this matters:** If the Choi homogeneity concern applies here, changing
model names is not enough. We need to know whether Tyler wants stronger
protocol-level diversity than "different models + different frames."

**Question:** What diversity mechanism should be enforced in code?

- Option A: Keep current approach: cross-family models plus distinct reasoning
  frames
- Option B: Fixed analyst roles with distinct duties, such as skeptic,
  decomposer, verifier
- Option C: Add a critique/revision loop between analysts
- Option D: Partition or mask evidence so analysts reason over different views
- Option E: Another specific mechanism

**Default:** Option A for v1, with diversity judged by benchmark results rather
than more orchestration complexity.

---

## 6. Acceptance Harness

**Why this matters:** "Better than Perplexity" is a slogan until we define the
benchmark set, baselines, rubric, and pass threshold. This is the actual gate
for implementation decisions.

**Question:** What is the acceptance harness for v1?

Please answer in this shape:

- Benchmark questions:
- Required baselines:
- Scoring dimensions:
- Pass threshold:
- Is this an offline evaluation gate, a runtime flag, or both?

**Default:**

- Benchmark questions: current fixed 6-question set unless Tyler provides a new
  canonical set
- Required baselines: Perplexity Deep Research and one single-model
  same-evidence baseline
- Scoring dimensions: current blind judge dimensions plus provenance
  completeness
- Pass threshold: pipeline wins on at least 4/6 with no provenance regressions
- Evaluation mode: offline gate first; runtime validation can remain optional

---

## How To Respond

For each question, either say `use default` or answer in the requested shape.
Example:

> **Q2**
> Always required: self-contained statement, evidence IDs.
> Required when available in the source: study name, timeframe, measured
> outcome, at least one number.
> Acceptable fallback: mark `low_specificity`.
> Failure behavior: retry once, then drop.

We will turn the answers into code changes, schema updates, and explicit
acceptance criteria.
