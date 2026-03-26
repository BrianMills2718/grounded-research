# Tech Debt

Known issues not worth fixing now but should be addressed eventually.

## Code Quality

### Inline prompts (code review #4-5)
`collect.py` query generation and `source_quality.py` scoring prompts are
inline Python strings, not YAML templates. Violates CLAUDE.md rule 8
("Prompts as Data"). Won't change output quality but hurts maintainability.

**Files:** `src/grounded_research/collect.py:84-96,114-128`, `src/grounded_research/source_quality.py:73-80`
**Fix:** Move to `prompts/query_generation.yaml` and `prompts/source_scoring.yaml`

### Hardcoded truncation in prompts (code review #12-13)
`synthesis.yaml` caps evidence at `evidence[:30]` and `long_report.yaml`
truncates content at `content[:400]`. Both hardcoded in Jinja2 templates,
not configurable via config.yaml. The two prompts also use different limits
(`[:500]` vs `[:400]`) with no documented reason.

**Files:** `prompts/synthesis.yaml:35`, `prompts/long_report.yaml:188`
**Fix:** Move to `evidence_policy.synthesis_evidence_cap` and `evidence_policy.content_truncation_chars` in config.yaml

### Counterarguments schema fragility (code review #14)
`AnalystRun.counterarguments` has `default_factory=list` AND `min_length=1`.
Works because Pydantic v2 doesn't validate defaults from `default_factory`.
If Pydantic changes this behavior, failed AnalystRun creation (which passes
no counterarguments) will break.

**File:** `src/grounded_research/models.py:412-414`
**Fix:** Use a validator that enforces min_length only when `error is None`

### PhaseTrace post-creation mutation (code review #15)
`engine.py:255` mutates `PhaseTrace.llm_calls` after appending to
`state.phase_traces`. The trace is correct at write time but the mutation
pattern is fragile — any code reading the trace between append and mutation
would see wrong data.

**File:** `engine.py:255`
**Fix:** Create PhaseTrace after all phase work is done, not before

## Pipeline Issues

### Dedup 0-groups bug (recurring)
OpenRouter/Gemini sometimes returns 0 groups from valid raw claims. The
1:1 fallback preserves data but means no dedup happened. Root cause unclear —
may be a structured output parsing issue with OpenRouter's Gemini routing.

**File:** `src/grounded_research/canonicalize.py:139-151`
**Frequency:** ~30% of runs via OpenRouter
**Fix:** Investigate whether the prompt or schema needs adjustment for OpenRouter routing. Consider a retry before falling back.

### Enumeration-heavy dedup instability
Dense claim sets from enumeration-heavy questions can still defeat the dedup
stage even after the retry guard. On the 2026-03-25 UBI rerun, a 47-claim set
produced one invalid dedup result, one invalid retry result, and then fell back
to 1:1 promotion. This preserved claims but inflated the canonical ledger and
likely weakened downstream dispute localization.

**File:** `src/grounded_research/canonicalize.py`
**Observed:** UBI post-Wave-1 benchmark (`output/ubi_wave1_post/trace.json`)
**Fix:** Add stronger non-merge guidance for enumeration questions, consider chunked or staged dedup, and treat repeated fallback on dense claim sets as a first-class benchmark failure.

Follow-up benchmark signal: the clean Wave 2 UBI rerun avoided the explicit
fallback path but still produced `40 raw -> 40 canonical` claims with only 3
disputes. That is an improvement in structural integrity, but it still suggests
weak canonical merging on dense enumeration-style questions.

### Claim extraction evidence-ID hallucination
The Claimify stage still invents invalid evidence/source identifiers on hard
questions. The current code strips bad IDs and now drops claims that become
ungrounded after cleanup, which prevents ledger pollution but can also discard
otherwise valuable claims when the model fails to anchor them correctly.

**File:** `src/grounded_research/canonicalize.py`
**Observed:** 2026-03-25 UBI reruns produced repeated invalid IDs such as `S-...`,
`C1-def-...`, and nonexistent `E-...` values during claim extraction.
**Fix:** Tighten the Claimify prompt/schema so only provided `E-...` IDs are valid outputs, consider presenting a smaller explicit candidate list, and add benchmark checks for dropped claims caused by evidence cleanup.

### PDF retrieval depends on missing optional parser
Study-heavy questions are currently penalized when important PDFs require the
`llama_cloud` parsing path and that dependency is not installed. The UBI run
lost access to several NBER, IZA, World Bank, and IMF PDFs this way.

**Files:** `src/grounded_research/tools/fetch_page.py`, environment setup
**Observed:** 2026-03-25 UBI rerun logged multiple `No module named 'llama_cloud'`
fetch failures during collection.
**Fix:** Either install the dependency as part of the supported environment, or replace the PDF path with a supported parser/fallback that does not silently reduce evidence quality on study-heavy questions.

Follow-up benchmark signal at that stage: local-first PDF parsing materially
improved the UBI collection pass to 99 evidence items, 2 gaps, and 26
authoritative sources, but the downstream report still lost 20 vs 24 to
Perplexity. Later coverage-breadth and report-calibration slices recovered the
benchmark, confirming retrieval was a real bottleneck but not the only one.

### Shared observability DB can kill long benchmark runs
Long UBI runs can fail in Phase 5 if `llm_client` budget accounting reads from
the shared observability SQLite database while other workloads hold it open.
The clean 2026-03-25 Wave 2 UBI rerun completed through adjudication and then
failed on `sqlite3.OperationalError: database is locked` before report
generation.

**Files:** external dependency in `~/projects/llm_client`, surfaced by `engine.py`
**Observed:** `output/ubi_wave2_full/trace.json` completed through adjudication;
report generation succeeded only after resuming export with an isolated
`LLM_CLIENT_DB_PATH`.
Project-local mitigation landed on 2026-03-26: pipeline runs now configure a
run-local `LLM_CLIENT_DB_PATH` under the output directory by default.

**Remaining fix:** `llm_client` should still become more robust under true
concurrent multi-process readers/writers so projects do not all need this
mitigation policy forever.

### Provider response hangs can stall long structured calls indefinitely
Bundle-based UBI retries showed OpenRouter-backed structured calls can sit in
HTTP response-body reads indefinitely when timeout policy bans explicit
request timeouts. This made a full pipeline retry stall during Claimify despite
the earlier clean raw-question run proving the phase could complete.

**Files:** external dependency in `~/projects/llm_client` and provider path in LiteLLM/OpenRouter
**Observed:** interrupted retry stack showed the process blocked in
`httpx`/`aiohttp` response reads during `extract_raw_claims()`.
Project-local mitigation landed on 2026-03-26: grounded-research now passes
config-driven finite request timeouts through the long-running `llm_client`
call sites.

**Remaining fix:** confirm on real completed benchmark runs that later-stage
provider hangs are eliminated, then decide whether shared-infra stuck-call
detection is still necessary.

Follow-up benchmark signal: serializing claim extraction removed the earlier
Phase 3a timeout failure on the improved 2026-03-25 UBI bundle, but a rerun
still stalled later in Phase 4 arbitration on the same provider timeout class.
The active reliability problem is now broader than claim extraction fan-out.

Follow-up on 2026-03-26: the project-local runtime policy now completes the
improved-bundle UBI run end-to-end under a run-local observability DB and
explicit finite request timeouts. The remaining shared-infra issue is
durability and nicer defaults in `llm_client`, not a current grounded-research
blocker.

### Benchmark comparison harness still uses stale timeout-policy defaults
The pipeline itself now runs under a benchmark-safe runtime policy, but
`scripts/compare_fair.py` still logs `LLM_CLIENT_TIMEOUT_POLICY=ban` and
disables explicit request timeouts. This no longer blocks comparisons in the
current environment, but it is inconsistent with the safer runtime policy used
by the pipeline itself.

**Files:** `scripts/compare_fair.py` and/or shared `llm_client` call-site policy
**Observed:** 2026-03-26 fair comparisons for `output/ubi_wave2_coverage_breadth/`
and `output/ubi_wave2_report_calibrated/`
**Fix:** Run benchmark/comparison scripts under the same explicit timeout policy
as the pipeline so long judge calls fail predictably instead of waiting indefinitely.

### Verification-time retrieval still has weak trace propagation
Wave 0 tool-call observability landed for collection, but the improved UBI
reruns showed verification-time Brave searches still writing `tool_calls` rows
with missing `trace_id`. That weakens diagnostics exactly where dispute
verification matters most.

**Files:** verification retrieval path in `src/grounded_research/verify.py` and shared retrieval wrappers
**Observed:** `output/ubi_wave2_coverage_breadth/llm_observability.db`
**Fix:** propagate `trace_id`/`task` through verification query search/fetch so dispute-resolution retrieval is queryable end-to-end.

### Sub-question evidence tagging incomplete
Evidence items are tagged with `sub_question_id` based on which search query
found them. But `_select_diverse()` round-robins across queries, and the
tag only comes from the first query that found a URL. If a source was found
by multiple sub-question queries, only the first tag survives. This causes
sub-questions to show 0 evidence even when relevant evidence exists.

**File:** `src/grounded_research/collect.py:235-250`
**Observed:** LLM SWE question had 3 sub-questions with 0 evidence despite 94 total items
**Fix:** Tag evidence by checking content relevance against sub-questions (LLM call), not just search query origin
