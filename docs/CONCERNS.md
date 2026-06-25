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
| GR-TYLER-TRACE-002 | Current Tyler traceability validates references and matrix links, not that every closed requirement has the right evidence kind. | High | `scripts/check_tyler_traceability.py` exposes current weak spots. | Implement the structured coverage plan in `docs/plans/tyler_requirements_traceability_program.md`. |
| GR-TYLER-TRACE-003 | Active docs may still disagree about remaining Tyler-required items. | Medium | Ledger and execution status are newer than older repo-map docs. | Run the planned doc-drift audit and reconcile or mark stale docs. |

## Portfolio Judgment

This is valuable portfolio work because it shows a real analyst-system design:
independent views, disagreement localization, fresh verification, and traceable
claims. The portfolio should emphasize adjudication and provenance, not a broad
"research agent" claim.
