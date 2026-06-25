# Grounded Research Concern Register

Wiki home: http://localhost:8088/index.php/Project_Wiki

## Open Concerns

| ID | Concern | Severity | Current mitigation | Next evidence/action |
|---|---|---:|---|---|
| GR-PORT-001 | Benchmark wins can be overgeneralized. | High | README and validation docs scope comparisons to tracked cases. | Add a public benchmark note with dataset, judge, and comparison caveats. |
| GR-PORT-002 | Tyler compliance history is complex. | Medium | `docs/TYLER_SPEC_GAP_LEDGER.md` is the canonical truth surface. | Add a short wiki summary of open vs verified-fixed rows. |
| GR-PORT-003 | Research output can look authoritative even when disputes remain unresolved. | High | Claim ledger and dispute surfaces preserve unresolved items. | Show a public trace excerpt with unresolved or narrowed claims. |
| GR-PORT-004 | Retrieval quality may be mistaken for the project thesis. | Medium | Architecture docs state adjudication is the product. | Keep portfolio walkthrough centered on disagreement and verification. |
| GR-PORT-005 | Saved output artifacts are not yet packaged as a compact public reviewer bundle. | High | Existing docs identify output files and walkthrough expectations. | Produce one non-sensitive run bundle and source-to-claim walkthrough. |
| GR-PORT-006 | Cost and latency claims can drift if estimated from old runs. | Medium | Shared observability exists. | Query real `llm_client` observability rows before public cost claims. |
| GR-RUNTIME-001 | Stage 2 collection can continue after individual search/fetch failures, so a run may succeed with partial source coverage. | High | Tool failures are logged and failed fetches are excluded from evidence. | Define a Tyler-compatible minimum evidence/readout threshold before changing this from warning-and-continue to fail-loud. |
| GR-TYLER-TRACE-001 | The raw Tyler packet is ignored by git, so full requirements-audit reproduction currently depends on local untracked files. | High | Derived ledger and matrices are tracked. | Track a controlled source copy or document a deliberate exception with hashes. |
| GR-TYLER-TRACE-002 | Tyler traceability can regress if evidence kind checks are not kept in the gate. | High | `scripts/check_tyler_coverage.py` grades evidence, includes negative controls, and fails `make check` on grade-F rows. | Keep the grade-F gate in `make check`; promote the Markdown ledger to structured data before broadening the policy. |
| GR-TYLER-TRACE-003 | Active docs may still drift after future Tyler remediation. | Medium | `scripts/check_tyler_doc_drift.py` scans active docs for known stale Tyler status claims and fails `make check` on findings. | Expand the doc-drift rule set when new stale-claim families are discovered. |
| GR-TYLER-TRACE-004 | Binary closure labels can overstate confidence unless paired with source anchors, evidence grades, negative controls, and adversarial review. | High | Source-anchor debt is closed for the current ledger; `scripts/check_tyler_code_audit.py` audits current implementation/verification evidence; `docs/TYLER_INDEPENDENT_CLOSURE_REVIEW.md` records the adversarial pass. | Do not upgrade grade-B/C/D rows without evidence that satisfies their class policy. |
| GR-TYLER-S2-001 | Stage 2 query generation was previously overclosed as Tyler-literal. | High | Fixed on 2026-06-25 by restoring deterministic string/orchestrator templates and deleting the obsolete query-diversification model path. | Keep `tests/test_tyler_v1_stage2_runtime.py::test_generate_search_queries_tyler_v1_returns_routed_query_plans` and the coverage/doc-drift gates active. |

## Portfolio Judgment

This is valuable portfolio work because it shows a real analyst-system design:
independent views, disagreement localization, fresh verification, and traceable
claims. The portfolio should emphasize adjudication and provenance, not a broad
"research agent" claim.
