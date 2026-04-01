Everything Missing or Deviated
Data Model Gaps

EvidenceLabel enum (4-level hierarchy with weights) — Without it, a vendor marketing claim and a peer-reviewed benchmark get the same treatment during arbitration
StageSummary model — No per-stage reasoning capture means the "process summary" report component can't exist and debugging is harder
AssumptionSetEntry as canonical artifact — Assumptions stay trapped inside analyst runs instead of being tracked, challenged, and reported as first-class objects
ClaimStatus lifecycle (8 → 5 values) — Missing pre-verification states (contested, contradicted) means the pipeline can't distinguish "models disagree" from "evidence conflicts" before Stage 5
DisputeType "other" catch-all — Edge-case disputes silently become "ambiguity" instead of being flagged for human judgment
DisputeStatus enum (4 → boolean) — Can't distinguish "deferred to user" from "logged only" from "resolved" — just resolved or not
ModelPosition on disputes — No record of what each analyst believed about the conflict, reducing arbitration context
ExtractionStatistics — No structured telemetry on claim extraction quality; minor, only affects debugging
Supporting/contesting model tracking on claims — Can't see which analysts agree/disagree on a specific claim
Output Contract Gaps

Structured tradeoffs (Tier A, component 3) — No "if you optimize for X → A, if Y → B" objects; tradeoff logic only appears in prose
Key assumptions (Tier B, component 6) — Not surfaced in the report; user can't see which assumptions could flip the recommendation
Confidence assessment (Tier B, component 7) — No per-claim confidence in the report; user can't gauge which parts of the recommendation are solid vs thin
Process summary (Tier B, component 8) — No scannable "how we got here" section; user has to read the full trace to understand the pipeline's reasoning
Claim ledger excerpt (Tier C, component 9) — Decision-critical claims not surfaced in structured form; user can't audit the evidence chain without opening trace.json
Evidence trail (Tier C, component 10) — No structured source-to-conclusion mapping in the report
Prompt Gaps

SHARED_OUTPUT_PROTOCOL on 12 of 13 prompts — Each prompt independently reinvents behavioral rules (or doesn't), causing inconsistent behavior across stages
DECISION_PROTOCOL block — The 6 cross-cutting invariants (independence, claims over prose, no social framing, no unlabeled claims, preserve lineage, don't polish uncertainty) appear nowhere as a named block
REASONING_REQUIREMENT block — Not explicitly present; some prompts ask for reasoning, others don't
Context anchoring at end of prompts (Constraint #10) — No prompt repeats the query at the bottom; with long inputs the model loses track of the original question
Evidence labeling hierarchy in all prompts — Not a single prompt mentions the 4-level hierarchy; the core evidence-weighting mechanism exists only in the spec
Dispute-adaptive synthesis rules — Synthesis prompt treats all disputes identically; the 4 conditional rendering paths don't exist
Subordination principle in synthesis — No "you are NOT generating a fresh answer" guard; the synthesis model can override pipeline arbitration
Anti-pattern guidance in synthesis (6 items) — No warnings about evidence laundering, false consensus, vague hedging, deep nesting, re-opening resolved disputes, or false closure
Self-check instruction in decompose prompt — No "before finalizing, verify completeness and neutrality" block
AVeriTeC-style neutral query framing (Stage 5) — Verification queries aren't structured as neutral/weaker-position/authoritative; just general "find clarifying evidence"
Quote preservation in evidence extraction — No original_quote field; conflict-bearing verbatim quotes are paraphrased away, introducing harmonization bias
Runtime Validation Gaps

Zombie check — One of only 2 spec-required runtime checks doesn't exist and can't be implemented because alternatives are plain strings with no claim ID references
Grounding errors are non-fatal — Pipeline continues and outputs the report even if grounding validation fails; spec implies reject-and-retry should block
Search & Model Gaps

Tavily + Exa dual-API routing → Brave only — No semantic search, no academic paper category, no content chunking (chunks_per_source); reduces source diversity for conceptual and scholarly topics
No Claude models anywhere — Spec assigns Claude to independent analysis (constitutional AI reasoning) and arbitration (lowest prompt injection rate); zero Anthropic models in the pipeline
Frontier models → budget models — gpt-5-nano and gemini-2.5-flash replace GPT-5.4, Claude Opus 4.6, Gemini 3.1 Pro; the spec's theory depends on "genuine capability differences between frontier models"
Stage 4 fallback: same model (gpt-5-nano → gpt-5-nano) — Spec requires cross-family fallback (GPT → Claude); code falls back to the same model, providing no resilience against model-specific failures
Design Constraint Gaps

Constraint #5 fully unimplemented — Evidence labeling hierarchy absent from model, prompts, and code
Constraint #10 partially unimplemented — Query at start only, never at end
Constraint #4 partially unimplemented — Claim status is point-in-time, not a change history; no lineage log per claim
Source Quality Gaps

Blended quality_score (authority + freshness decay) — Spec's continuous 0-1 score with half-life decay replaced by 4-level categorical tier; no freshness weighting
Staleness detection (3 regex checks) — Deprecation keywords, version-in-URL, year-mention checks not implemented
Research priority per sub-question — No high/medium/low priority to guide budget allocation across sub-questions
Search guidance per sub-question — No per-SQ instructions flowing from decomposition to evidence collection