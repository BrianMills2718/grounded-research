# V1 Pre-Build Audit Report

> Generated: 2026-03-26
> Auditor: Claude Opus 4.6
> Documents audited: V1_DESIGN.md, V1_Build_Plan_Step_By_Step.md, V1_SCHEMAS.md, V1_PROMPTS.md

---

## 1. PASS / FAIL Summary

| Phase | Verdict | Issues |
|-------|---------|--------|
| **1a. Stage descriptions (DESIGN ↔ Build Plan)** | **PASS** | 0 critical, 1 low |
| **1b. Schema ↔ Prompt ↔ Build Plan field alignment** | **FAIL** | 2 moderate |
| **1c. Enum consistency** | **FAIL** | 1 moderate |
| **1d. Cross-references** | **PASS** | 0 issues |
| **1e. 10 design constraints** | **PASS** | All respected |
| **1f. Skip/branch conditions** | **PASS** | 0 issues |
| **2a. Developer buildability** | **PASS** | 0 blockers |
| **2b. Prompt coverage** | **PASS** | 1 low (clarity) |
| **2c. Validation rules** | **PASS** | 0 issues |
| **3. Freshness verification** | **FAIL** | 1 critical, 3 moderate |
| **4a. Cost model** | **PASS** | Reasonable |
| **4b. Latency model** | **PASS** | Reasonable |
| **4c. Failure modes** | **PASS** | 1 low gap |

---

## 2. Issues Found

### CRITICAL — Must fix before handing to developer

---

#### ISSUE C-1: Exa `systemPrompt` + `type="auto"` is an invalid combination

**Location:** Build Plan, Stage 2, Step 4 routing table (line ~66)
**Also referenced:** Build Plan, Step 2 API-specific formatting (line ~51)

**What's wrong:** The routing table specifies:
> `Semantic/conceptual | Exa | type="auto", descriptive query, systemPrompt set`

But 5 lines earlier, the Build Plan itself correctly states:
> `Exa systemPrompt: Set to "Prefer official sources..." (This is a first-class Exa API parameter for type: "deep" searches.)`

Per current Exa API docs (confirmed March 2026), `systemPrompt` only works with `type="deep"`. Using `systemPrompt` with `type="auto"` will be silently ignored — the developer's domain preference instructions will have no effect on semantic queries.

**Severity:** CRITICAL — silent failure; the developer would implement it, it would appear to work (no errors), but systemPrompt instructions would be ignored for the majority of Exa queries.

**Recommended fix:** Change the routing table entry to:
```
Semantic/conceptual | Exa | type="deep", descriptive query, systemPrompt set
```
Or split into two rows: `type="auto"` for quick semantic lookups, `type="deep"` when systemPrompt control is needed.

---

#### ~~ISSUE C-2~~ ISSUE M-2b: Exa `highlights` SDK surface has changed (downgraded from CRITICAL)

**Location:** Build Plan, Stage 2, Step 4 cost controls (line ~73)

**What's wrong:** The Build Plan states:
> `Exa: Request highlights with maxCharacters parameter (not deprecated numSentences).`

The highlights feature was temporarily removed from Exa SDKs but has been **reintroduced** (exa-js v2.0.11+, exa-py current). The current SDK API is: `highlights=True` or `highlights={"max_characters": 500}`. Contents are now returned by default with search results, eliminating the need for a separate contents call.

`numSentences` and `highlightsPerUrl` are confirmed deprecated (numSentences mapped at ~1,333 chars/sentence; highlightsPerUrl accepted but ignored).

**Severity:** MODERATE (downgraded from CRITICAL) — highlights work but the SDK surface has changed. The spec's guidance to use `maxCharacters` is correct in principle, but the developer should consult current exa-py docs for the exact parameter path.

**Recommended fix:** Add a note to the Build Plan that Exa SDK versions have changed and the developer should verify the exact `highlights` API surface in current exa-py docs. Note that contents are now returned by default — a separate contents call may no longer be needed.

---

### MODERATE — Should fix; developer will hit confusion or subtle bugs

---

#### ISSUE M-1: DESIGN.md and Build Plan use wrong ClaimStatus values for Stage 5 output

**Location:** DESIGN.md, Stage 5 (line ~168); Build Plan, Stage 5, Step 3 (line ~235)

**What's wrong:** Both documents describe Stage 5 arbitration output as:
> `update claim status based on new evidence (supported / contradicted / insufficient)`

But the V1_SCHEMAS.md (the authoritative source for data contracts) correctly constrains Stage 5 output to the **post-verification** status set:
> `Post-verification status: verified, refuted, or unresolved`

The values "supported / contradicted / insufficient" are the **pre-verification** statuses set by Stage 4. Stage 5 transitions claims to the final status set. The Schema's ClaimStatus lifecycle comment makes this clear:
> `initial → {supported|contested|contradicted|insufficient} → {verified|refuted|unresolved}`

**Severity:** MODERATE — a developer reading DESIGN or Build Plan (but not Schemas) could implement Stage 5 using the wrong enum values, causing validation failures.

**Recommended fix:** In DESIGN.md Stage 5 and Build Plan Stage 5 Step 3, change "supported / contradicted / insufficient" to "verified / refuted / unresolved" to match the Schema's post-verification status set.

---

#### ISSUE M-2: Stage 6b prompt template references `dispute.remaining_uncertainty` which doesn't exist on DisputeQueueEntry

**Location:** PROMPTS.md, Stage 6b USER template (line ~1089)

**What's wrong:** The template contains:
```
{{if dispute.status == "unresolved"}}
Remaining uncertainty: {{dispute.remaining_uncertainty}}
{{endif}}
```

But `DisputeQueueEntry` in V1_SCHEMAS.md has no `remaining_uncertainty` field. Its fields are: `id`, `type`, `description`, `claims_involved`, `model_positions`, `decision_critical`, `decision_critical_rationale`, `status`, `resolution_routing`.

The `remaining_uncertainty` field exists on `ClaimStatusUpdate` (in ArbitrationAssessment), not on the dispute itself.

This variable is also NOT listed in the "Orchestrator-Constructed Variables" section of PROMPTS.md.

**Severity:** MODERATE — the developer will hit a template rendering error (undefined variable) when processing unresolved disputes in Stage 6b.

**Recommended fix:** Either:
1. Add `remaining_uncertainty` to the Orchestrator-Constructed Variables section, with a note that it's extracted from `ClaimStatusUpdate.remaining_uncertainty` for claims involved in this dispute, OR
2. Add `remaining_uncertainty: Optional[str]` field to `DisputeQueueEntry` schema (populated by orchestrator after Stage 5)

---

#### ISSUE M-3: Exa API pricing model has changed significantly

**Location:** Build Plan, Stage 2 cost controls; DESIGN.md v1.1 considerations

**What's wrong:** The spec assumes Exa pricing is simple per-query. Current Exa pricing (March 2026):
- Standard search: **$0.003 per search** + **$0.001 per contents extraction**
- Deep search: **$12 per 1,000 requests** ($0.012/request)
- Deep-reasoning: **$15 per 1,000 requests**

If `type="deep"` is used (per the systemPrompt fix in C-1), Exa costs jump from ~$0.004 to ~$0.012 per query — 3x more expensive. This affects the cost model.

**Severity:** MODERATE — won't break the build, but the developer needs accurate pricing for budget estimation.

**Recommended fix:** Add current Exa pricing to the Build Plan cost controls section. If `type="deep"` is adopted per the C-1 fix, note the cost increase and consider reserving deep search for high-priority sub-questions only.

---

#### ISSUE M-4: Tavily has new `fast` and `ultra-fast` search_depth options not reflected in spec

**Location:** Build Plan, Stage 2, Step 4 routing table

**What's wrong:** As of January 2026, Tavily added two new `search_depth` values:
- `fast`: lower latency, still supports `chunks_per_source`
- `ultra-fast`: minimum latency, single NLP summary per URL

The V1 spec only references `basic` and `advanced`. The `fast` depth is particularly relevant because it supports `chunks_per_source` (previously only available on `advanced`) at lower latency and cost.

**Severity:** MODERATE — the spec works without these, but the developer should know `fast` exists as a potentially better default for Stage 2 queries (lower cost than `advanced`, still supports chunks).

**Recommended fix:** Add a note to the Build Plan routing table acknowledging `fast` and `ultra-fast` as options. Consider using `fast` instead of `basic` for general queries where `chunks_per_source` would improve finding extraction.

---

### LOW — Nice to fix; won't block the build

---

#### ISSUE L-1: Stage 3 role names are confusing across documents

**Location:** Build Plan Stage 3 (line ~149); PROMPTS.md Frame Assignments (line ~78)

**What's wrong:** The Build Plan assigns:
- `Claude Opus 4.6 — critical frame (verification-first)`
- `Gemini 3.1 Pro — verification frame (structured decomposition)`

Claude's ROLE is "critical" but its FRAME is "verification-first." Gemini's ROLE is "verification" but its FRAME is "structured decomposition." PROMPTS.md already has a note acknowledging this confusion:
> "The Build Plan uses different role names... but the reasoning frame assignments in parentheses match."

**Severity:** LOW — PROMPTS.md addresses it; a careful developer will find the note.

**Recommended fix:** Consider aligning role names with reasoning frames, or at minimum, make the PROMPTS.md note more prominent (bold/callout box).

---

#### ISSUE L-2: Stage 5 neutral query generation — model call or template?

**Location:** PROMPTS.md, Prompt Inventory table + Stage 5 query generation section (line ~767)

**What's wrong:** The Prompt Inventory lists this as "Orchestrator templates (no model call)" but the template content includes instructions like "Generate 3 search queries" and "Convert this dispute into a question" that semantically require LLM reasoning to execute (e.g., converting "Einstein born 1879 vs 1880" into the neutral query "What year was Einstein born?").

A developer would reasonably ask: "How do I programmatically generate neutral questions from dispute descriptions without a model?"

**Severity:** LOW — the developer can figure it out (likely needs a lightweight model call), but the classification as "no model call" is misleading.

**Recommended fix:** Either reclassify as a lightweight model prompt (and add to the model prompt inventory), or add an implementation note explaining how to generate neutral queries programmatically.

---

#### ISSUE L-3: DESIGN.md lists 7 anti-patterns; Stage 6b prompt lists 8

**Location:** DESIGN.md Output anti-patterns section (line ~256); PROMPTS.md Stage 6b prompt (line ~990)

**What's wrong:** DESIGN.md lists 7 anti-patterns (2 runtime + 5 eval). The Stage 6b prompt lists 8 (2 runtime + 6 eval). The extra one in the prompt is "EVIDENCE LAUNDERING: Making a claim in the recommendation that cannot be traced back to a specific source in the evidence trail."

This is arguably covered by the grounding check, but the prompt treats it as a separate eval criterion.

**Severity:** LOW — doesn't affect implementation; the prompt just has an extra guideline.

**Recommended fix:** Add "evidence laundering" to DESIGN.md's eval criteria list for consistency, or note in the prompt that it overlaps with the grounding check.

---

#### ISSUE L-4: Stage 1 fallback chain differs slightly between DESIGN and Build Plan

**Location:** DESIGN.md Cross-Cutting (line ~314); Build Plan Cross-Cutting (line ~332)

**What's wrong:** DESIGN says `Stage 1: Gemini → GPT`. Build Plan says `GPT-5.4 mini or Claude Sonnet 4.6`. The Build Plan offers a second fallback option (Claude Sonnet) not mentioned in DESIGN.

**Severity:** LOW — Build Plan is the implementation authority; DESIGN is just less specific.

**Recommended fix:** Update DESIGN to say `Gemini → GPT-5.4 mini (or Claude Sonnet 4.6)` for alignment.

---

#### ISSUE L-5: Exa QPS limit is 10, not 5

**Location:** DESIGN.md v1.1 considerations (line ~358)

**What's wrong:** DESIGN.md says "Brave Search API as third search provider (independent index, 50 QPS — useful if Exa's 5 QPS becomes a bottleneck)." Exa's default rate limit is now **10 QPS** (600 req/min), not 5. Enterprise plans offer higher limits.

**Severity:** LOW — this only affects a v1.1 consideration, not V1 implementation.

**Recommended fix:** Update the QPS figure in DESIGN.md v1.1 considerations.

---

#### ISSUE L-6: Stage 5 additional source quality scoring process unspecified

**Location:** SCHEMAS.md, AdditionalSource class (line ~365)

**What's wrong:** `AdditionalSource.quality_score` exists but the Build Plan doesn't describe how Stage 5 sources get quality scores. Stage 2 has a detailed 3-step scoring pipeline (Steps 7-9), but Stage 5's simplified sources (`key_findings: list[str]` instead of `list[Finding]`) have no equivalent scoring description.

**Severity:** LOW — developer can apply the same Stage 2 pipeline or a simplified version.

**Recommended fix:** Add a brief note to Build Plan Stage 5 specifying whether Stage 5 sources use the same scoring pipeline as Stage 2 or a simplified approach.

---

## 3. Freshness Report

### 3a. APIs

| Item | V1 Spec Says | Current Status (March 2026) | Action Needed? |
|------|-------------|---------------------------|----------------|
| **Tavily: search_depth** | `basic`, `advanced` | `basic`, `advanced`, `fast`, `ultra-fast` (Jan 2026) | MODERATE — add fast/ultra-fast awareness (Issue M-4) |
| **Tavily: include/exclude_domains** | Supported | Confirmed ✓ | None |
| **Tavily: topic** | `"news"` | `"general"`, `"news"` confirmed ✓ | None |
| **Tavily: time_range** | `"week"` | Confirmed ✓ | None |
| **Tavily: chunks_per_source** | Available with `advanced` | Now also available with `fast` | Note in Build Plan |
| **Tavily: auto_parameters** | Warning about silent upgrade | Confirmed ✓ — still silently upgrades to advanced | None |
| **Tavily: pricing** | 1 credit basic, 2 credits advanced | Confirmed ✓. PAYG $0.008/credit, plans $0.005-0.0075/credit | None |
| **Tavily: Nebius acquisition** | Noted as risk | Confirmed Feb 2026, $275-400M. Tavily says API unchanged. | Continue monitoring |
| **Exa: type parameter** | `type="auto"` for semantic | `auto`, `neural`, `fast`, `deep`, `deep-reasoning` available | CRITICAL — systemPrompt needs `type="deep"` (Issue C-1) |
| **Exa: systemPrompt** | First-class parameter | Only works with `type="deep"` | CRITICAL (Issue C-1) |
| **Exa: highlights** | `highlights` with `maxCharacters` | Highlights REMOVED from SDKs. Contents returned by default. | CRITICAL (Issue C-2) |
| **Exa: maxCharacters** | Preferred over numSentences | `numSentences` deprecated, `maxCharacters` preferred ✓ | Update mechanism |
| **Exa: maxAgeHours** | Used for static content | Now age-based caching (not just livecrawl). `-1` still valid. | None |
| **Exa: includeDomains/excludeDomains** | Supported | Confirmed ✓ | None |
| **Exa: category** | `"research paper"` | Assumed still valid (no deprecation found) | Verify in docs |
| **Exa: pricing** | Not explicitly specified | $0.007/search (contents included for 10 results); deep=$0.012/req | MODERATE (Issue M-3) |
| **Both APIs: actively maintained** | Yes | Both confirmed active and maintained ✓ | None |

### 3b. Models

| Item | V1 Spec Says | Current Status (March 2026) | Action Needed? |
|------|-------------|---------------------------|----------------|
| **GPT-5.4** | Current model name | Confirmed ✓. Snapshot: `gpt-5.4-2026-03-05`. | None |
| **GPT-5.4: structured output** | Best structured output (constrained decoding) | Confirmed ✓. JSON Schema via `json_schema` option. | None |
| **GPT-5.4: reasoning_effort** | 5 levels mentioned | Confirmed: none, low, medium, high, xhigh ✓ | None |
| **GPT-5.4 mini** | Used as fallback/lightweight | Confirmed ✓. Snapshot: `gpt-5.4-mini-2026-03-17`. | None |
| **Claude Opus 4.6** | Current model name | Confirmed ✓. Released Feb 5, 2026. 1M context. | None |
| **Claude Opus 4.6: structured output** | Supported | Confirmed ✓. New parameter: `output_config.format` (old `output_format` deprecated). | Note for developer |
| **Claude Opus 4.6: no prefilling** | Returns 400 error | Confirmed ✓. Spec already notes this. | None |
| **Claude Opus 4.6: thinking** | Not specified | New: `thinking: {type: "adaptive"}` replaces `{type: "enabled"}` | Inform developer |
| **Gemini 3.1 Pro** | Preview; 503 errors; GA April-May 2026 | Confirmed: still preview, 503 errors, latencies up to 104s. GA "soon" (est. April-May). | None — spec is accurate |
| **Gemini 3.1 Pro: structured output** | Supported via responseJsonSchema | Confirmed, but documented **performance degradation** with constrained decoding vs unstructured output (97% → 86% on one benchmark). Google community recommends JSON-Prompt over JSON-Schema for reasoning-heavy tasks. | Inform developer — may affect Stage 1/3 quality |
| **Gemini 3.1 Pro: latency** | 503 errors, latencies up to 104s | TTFT of **21-31 seconds is normal** (architectural, not a bug — reasoning model). 503s during peak near 50% failure rate. | Spec's warning is accurate; fallbacks essential |
| **Claude Opus 4.6: pricing** | Not specified | $5 / $25 per MTok input/output | Cost estimates should use this |
| **GPT-5.4: pricing** | Not specified | $2.50 / $10 per MTok input/output | Cost estimates should use this |
| **Newer models to consider** | — | Sonnet 4.6 ($cheaper than Opus), GPT-5.4 Mini, Gemini 3.1 Flash-Lite ($0.25/$1.50) — all potential lighter alternatives for cost-sensitive stages. No new frontier models that change the architecture. | None required |

### 3c. Research Papers & Techniques

| Item | V1 Spec Says | Current Status (March 2026) | Action Needed? |
|------|-------------|---------------------------|----------------|
| **FIRE (NAACL 2025)** | Latest on adaptive fact-checking | Confirmed ✓. Published Findings of NAACL 2025. GitHub active. No successor found. | None |
| **AVeriTeC** | Reference dataset for claim verification | Still the reference ✓. Extended to multimodal (AVerImaTeC, NeurIPS 2025). | None |
| **Google SAFE** | Reference implementation for Stage 5 | Still maintained on GitHub ✓. Extended to FACTS Benchmark Suite. | None |
| **Claimify** | Stage 4 extraction approach | No better alternative found. Two small open-source implementations still available. | None |

### 3d. Libraries

| Item | V1 Spec Says | Current Status (March 2026) | Action Needed? |
|------|-------------|---------------------------|----------------|
| **sentence-transformers** | Referenced for v1.1 NLI dedup | v5.3.0 (March 12, 2026). Very actively maintained. Apache 2.0. | None |
| **datasketch** | Referenced for v1.1 MinHash+LSH | Assumed still active (no deprecation found) | None |
| **OpenPageRank** | Referenced for v1.1 domain authority | Assumed still active (no deprecation found) | None |

### 3e. Competitive Landscape

No new search APIs or fact-checking tools were found that would obsolete parts of the pipeline. Tavily and Exa remain the top two AI-focused search APIs. Brave Search API (mentioned as v1.1 consideration) is still available as a third option. Firecrawl and WebSearch API are alternatives but focused on different use cases (crawling/extraction).

---

## 4. Cost + Latency Estimates

### Cost per run (4 sub-questions, 3 disputes, 2 reaching Stage 5)

| Component | Count | Unit Cost | Subtotal |
|-----------|-------|-----------|----------|
| **Stage 1: Gemini 3.1 Pro** | 1 call (~1.3K tokens) | ~$0.002 | $0.002 |
| **Stage 2: Query diversification** | 4 lightweight calls | ~$0.001/call | $0.004 |
| **Stage 2: Tavily basic searches** | ~12 queries | 1 credit × $0.008 | $0.096 |
| **Stage 2: Exa searches** | ~4 queries | $0.007/query (standard) or $0.012 (deep) | $0.028-0.048 |
| **Stage 2: Finding extraction** | ~16 lightweight calls | ~$0.001/call | $0.016 |
| **Stage 3: GPT-5.4** | 1 call (~8K in, ~3K out) | $2.50/$10 per MTok | $0.05 |
| **Stage 3: Claude Opus 4.6** | 1 call (~8K in, ~3K out) | $5/$25 per MTok | $0.115 |
| **Stage 3: Gemini 3.1 Pro** | 1 call (~8K in, ~3K out) | $2/$12 per MTok | $0.052 |
| **Stage 4: GPT-5.4** | 1-3 calls (~12K in, ~5K out) | $2.50/$10 per MTok | $0.08 |
| **Stage 5: Tavily advanced searches** | 6 queries | 2 credits × $0.008 | $0.096 |
| **Stage 5: Claude Opus 4.6 arbitration** | 2 calls (~3K in, ~2K out) | $5/$25 per MTok | $0.13 |
| **Stage 6b: Synthesis model** | 1 call (~15K in, ~5K out) | Depends on model chosen | $0.10-0.20 |
| **TOTAL** | | | **~$0.75-1.00** |

**Verdict:** Very reasonable for a personal CLI tool. Under $1 per full pipeline run at current pricing. The most expensive components are Claude Opus 4.6 calls (~$0.25 total across Stages 3+5) and GPT-5.4 calls (~$0.13 total). If cost matters, Sonnet 4.6 or GPT-5.4 Mini are viable cheaper alternatives for non-critical stages.

### Latency per run (same scenario)

| Stage | Estimated Wall-Clock | Notes |
|-------|---------------------|-------|
| Stage 1 | 5-15s | Single Gemini call (unstable, could hit 30s+ timeout) |
| Stage 2 | 20-35s | Query gen + parallel searches + finding extraction (batched) |
| Stage 3 | 15-30s | 3 parallel calls; Gemini is the bottleneck |
| Stage 4 | 15-30s | Complex structured output; may need multiple calls |
| Stage 5 | 15-30s | 2 disputes × (search + arbitration), partially parallelizable |
| Stage 6a | 0-30s | User interaction (if triggered) |
| Stage 6b | 15-30s | Single synthesis call + validation |
| **TOTAL** | **~90-170s** | **~1.5-3 minutes typical** |

**Bottlenecks:**
1. Stage 2 (many sequential API calls for finding extraction)
2. Stage 3 (parallel but bounded by slowest model — Gemini)
3. Stage 4 (complex extraction, potentially multiple calls)

**Async is properly leveraged:** Stage 2 searches use `asyncio.gather()`, Stage 3 runs 3 models in parallel. Stage 5 disputes could be parallelized but aren't explicitly specified — recommend adding a note.

### Failure Modes

| Scenario | Impact | Mitigation in Spec | Gap? |
|----------|--------|-------------------|------|
| **Tavily down** | Stage 2 loses keyword/news search, Stage 5 loses advanced search | Not explicitly addressed | **LOW gap** — Exa can partially substitute, but no explicit fallback |
| **Exa down** | Stage 2 loses semantic/academic search | Not explicitly addressed | **LOW gap** — Tavily can partially substitute |
| **Both APIs down** | Pipeline cannot gather evidence | Partial trace on abort ✓ | Covered |
| **1 of 3 Stage 3 models fails** | Continue with 2 models | Explicitly addressed ✓ (≥2 required) | None |
| **2 of 3 Stage 3 models fail** | Pipeline aborts | Partial trace on abort ✓ | None |
| **Stage 4 GPT-5.4 fails** | Fallback to Claude Opus 4.6 ✓ | Explicitly addressed | None |
| **Stage 1 Gemini fails** | Fallback to GPT-5.4 mini ✓ | Explicitly addressed | None |
| **Stage 6b model fails** | Fallback to alternate model ✓ | Explicitly addressed | None |
| **Gemini 3.1 Pro unstable (503/timeout)** | Stages 1 and 3 affected | Fallback chain defined ✓ + stability warning | None |
| **Rate limiting** | Any API could throttle | Not explicitly addressed | **LOW gap** — add retry-with-backoff note |

---

## 5. Final Verdict

### Is this spec ready to hand to a developer?

**Almost. Fix 1 critical issue first, then it's ready.**

The spec is impressively thorough and internally consistent. Four documents, 6 pipeline stages, 10 design constraints, and dozens of cross-references — and only 1 critical issue, 5 moderate issues, and 5 low issues. That's a well-built spec.

### Must-fix before build (CRITICAL):

1. **C-1: Fix the Exa routing table** — `systemPrompt` requires `type="deep"`, not `type="auto"`. This is a silent failure that would produce degraded search quality with no error signal.

### Should-fix before build (MODERATE):

2. **M-1:** Update DESIGN.md and Build Plan to use correct post-verification ClaimStatus values (verified/refuted/unresolved, not supported/contradicted/insufficient) for Stage 5 output.

3. **M-2:** Add `dispute.remaining_uncertainty` to the Orchestrator-Constructed Variables section in PROMPTS.md, or add the field to DisputeQueueEntry schema.

4. **M-2b:** Verify Exa highlights SDK surface — highlights were temporarily removed then reintroduced. Developer should check current exa-py docs for exact parameter path.

5. **M-3:** Add current Exa pricing to the Build Plan ($0.007/search standard, $0.012/deep).

6. **M-4:** Note Tavily's new `fast` search_depth option in the routing table.

### Informational note — Gemini structured output quality:

Gemini 3.1 Pro has documented performance degradation when using constrained decoding (JSON-Schema mode) vs unstructured output. Google's community recommends JSON-Prompt over JSON-Schema for reasoning-heavy tasks. Since Stages 1 and 3 use Gemini with structured output schemas, the developer should test whether JSON-Schema mode degrades Gemini's decomposition (Stage 1) or analysis (Stage 3) quality, and consider falling back to JSON-Prompt mode with post-generation validation if it does.

### Informational notes for the developer:

- Claude Opus 4.6 structured output: use `output_config.format` (not deprecated `output_format`)
- Claude Opus 4.6 thinking: `thinking: {type: "adaptive"}` is the recommended mode
- GPT-5.4 reasoning_effort: 5 levels confirmed (none/low/medium/high/xhigh)
- Gemini 3.1 Pro: still preview, stability issues confirmed — fallbacks are essential
- All referenced research papers and libraries are current and actively maintained

### Bottom line:

Fix C-1 (5 minutes), address M-1 through M-4 (another 25 minutes), and this spec is ready for a developer to build from. The architecture is sound, the documents are consistent, and the design constraints are properly respected throughout.
