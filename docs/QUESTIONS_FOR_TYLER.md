# Questions for Tyler: Design Clarification

These questions address the gaps Tyler identified in his review. Each question
has a default answer that we'll implement if no response is given. Tyler should
override any defaults he disagrees with.

**How to respond:** For each question, give a concrete answer that we can
turn into a code change. "I think X is important" isn't actionable.
"Use approach (b) with these specific models" is.

If you don't care about a question, say "use default" and we'll implement
the default answer listed.

---

## 1. Reasoning Frames

**Context:** The pipeline uses 3 frames (verification-first, structured
decomposition, step-back abstraction) to force analytical divergence across
models. The Choi et al. "Artificial Hivemind" paper shows models converge on
similar outputs even across families.

**Question:** Are these the right 3 frames? Should we add/replace any?
In your manual cross-examination process, what analytical lenses produced
genuinely different conclusions on the same evidence?

**Default:** Keep current 3 frames. They're defined in `prompts/analyst.yaml`
and configurable in `config/config.yaml` — adding new frames is a config +
prompt change.

---

## 2. Scope

**Context:** The codebase now owns the full journey (question → search →
analyze → arbitrate → report). Tyler's review says the V1 is a "general-purpose
reasoning orchestrator" but CLAUDE.md says "adjudication-first, not a new
end-to-end research pipeline."

**Question:** Should this be positioned as general-purpose (any research
question) or specifically for contested/nuanced topics? On pure enumeration
questions (e.g., "list all UBI pilot programs") we lose to Perplexity. On
contested policy/science questions we win 5/5.

**Default:** General-purpose with a documented strength on contested topics.

---

## 3. Model Selection for Production

**Context:** We're using cheap models during development and testing
(GPT-5-nano, Gemini 2.5 Flash, DeepSeek Chat) to iterate fast without
burning money. These cheap models already win 5/6 vs Perplexity Deep
Research. Tyler's V1 specifies frontier models (GPT-5.4, Claude Opus
4.6, Gemini 3.1 Pro) — the pipeline is designed so you swap models via
config without code changes.

**Questions:**
- (a) Which specific models do you want for the 3 analyst slots when
  you actually use this? (We'll ship a `config/config_production.yaml`
  with your choices alongside the cheap testing config.)
- (b) Which model for synthesis?
- (c) What's your acceptable cost per run?
- (d) Should Claude be a 4th analyst (more disagreement, higher cost)
  or replace DeepSeek (keep 3 analysts)?

**Default:** Ship two configs: `config.yaml` (cheap, for testing/development)
and `config_production.yaml` (frontier models, for real use).

---

## 4. Claim Precision

**Context:** This is the #1 quality gap. Analysts see evidence containing
"The Finnish experiment (N=2,000, 2017-2018)" but produce claims like
"pilot programs show minimal effects." Prompt instructions to be specific
haven't solved it.

**Questions:**
- (a) In your manual process, how did you get study-level specificity?
  Did you ask follow-up questions? Paste source text back? Use a specific
  prompt pattern?
- (b) Should we add a post-extraction validation pass that checks claims
  for specificity and re-prompts if too abstract? (Adds ~$0.02/run)
- (c) Is this a model capability issue (cheap models can't extract specifics)
  or a prompt issue?

**Default:** Add claim validation pass. If >50% of claims lack named studies
or specific numbers, re-prompt the analyst with the relevant evidence items
and ask for revision.

---

## 5. Anti-Conformity Mechanism

**Context:** Tyler's V1 says "a model may only change position when citing
new evidence, a corrected assumption, or a resolved contradiction." Current
code checks that verdicts have new_evidence_ids but doesn't validate that
the evidence is relevant to the position change.

**Question:** What specifically should the validation check? Options:
- (a) LLM call: "Does evidence X support changing claim Y?" (adds ~$0.01/dispute)
- (b) Schema constraint: ArbitrationResult requires `justification` field
  that must reference specific evidence content, not just IDs
- (c) Both (a) and (b)
- (d) Something else — describe the mechanism

**Default:** Option (a) — post-arbitration LLM validation call.

---

## 6. Quality Validation

**Context:** We currently validate by comparing pipeline output against
Perplexity Deep Research using a blind LLM judge (5 dimensions, no provenance
bias). The pipeline wins 5/6 test questions. Tyler's V1 says the pipeline
should demonstrably outperform simpler approaches.

**Question:** What quality check do you want?
- (a) Keep current approach: compare against Perplexity via scripts when
  we want to validate (current — works well, not automated)
- (b) Add a `--validate` flag that automatically runs the pipeline output
  against Perplexity Deep Research and reports the score (adds ~$0.05 +
  Perplexity API cost per run)
- (c) Add a `--validate` flag that runs a single-model-playing-all-roles
  baseline (one LLM gets the same evidence and writes a report without
  the multi-analyst pipeline) and compares (adds ~$0.03 per run)
- (d) Both (b) and (c) — compare against Perplexity AND against a simpler
  single-model approach
- (e) Something else — describe what "demonstrably outperform" means to
  you in practice

**Default:** Option (a) — keep post-hoc comparison via scripts.

---

## 7. Acceptance Test

**Context:** When Tyler runs this on a question, we need to know what he
checks to evaluate quality.

**Questions:**
- (a) Does he read the report and judge subjectively?
- (b) Does he compare against Perplexity/GPT-Researcher output?
- (c) Does he check the trace.json for provenance completeness?
- (d) Does he have specific questions he plans to test on?
- (e) What's the minimum quality bar — "better than Perplexity on most
  questions" or "better than Perplexity on all questions" or something else?

**Default:** "Better than Perplexity on ≥4/6 diverse questions" (current: 5/6).

---

## How to Respond

For each question, just state your answer. Example:

> **Q3:** (a) GPT-5.4, Claude Opus 4.6, Gemini 3.1 Pro. (b) Claude Opus 4.6.
> (c) Up to $3/run. (d) Replace DeepSeek with Claude, keep 3 analysts.

We'll turn your responses into implementation tasks with specific file
changes and acceptance criteria.
