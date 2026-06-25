# Tyler Independent Closure Review

> Sources consulted: `docs/TYLER_AUDIT_QUALITY_STANDARD.md`;
> `docs/TYLER_SPEC_GAP_LEDGER.md`; `docs/TYLER_TRACEABILITY.md`;
> `docs/TYLER_REQUIREMENTS_COVERAGE_STATUS.md`;
> `scripts/check_tyler_coverage.py`; `scripts/check_tyler_doc_drift.py`;
> `scripts/check_tyler_code_audit.py`; sampled tests named below;
> codebase-memory fast index `home-brian-projects-grounded-research`
> (`1,165` nodes, `2,118` edges).
>
> Status: adversarial closure review checkpoint. This is not a PR-readiness
> claim.

## Review Scope

This review calibrated the current machine gates against the adversarial lane in
`docs/TYLER_AUDIT_QUALITY_STANDARD.md`.

Current generated readouts:

| Gate | Result |
|---|---:|
| Tyler requirements | 36 |
| Grade-F rows | 0 |
| Source-anchor pending rows | 0 |
| Line-level Tyler anchors | 31 |
| Explicit doc-governance anchor exceptions | 5 |
| Active-doc drift findings | 0 |
| Non-doc rows audited for current-code evidence | 24 |
| Current-code evidence gaps | 0 |

## Sampled Rows

| Row | Grade | Adversarial question | Disposition |
|---|---:|---|---|
| `S2-QUERY-MODEL-001` / `S2-QUERY-VARIANTS-001` | A | Does the test prove Tyler's string-template rule, not just local shape? | Pass. `tests/test_tyler_v1_stage2_runtime.py::test_generate_search_queries_tyler_v1_returns_routed_query_plans` fails if Stage 2 query generation calls `llm_client.acall_llm_structured`, asserts four Tyler query roles, basic Tavily depth, Exa chunk detail, and retrieval instruction. |
| `S2-ROUTING-001` | A | Does the test prove provider routing rather than just query count? | Pass. `tests/test_collect.py::test_collect_evidence_routes_tyler_query_plans_by_provider_role` builds typed Tavily and Exa query plans and checks forwarding behavior. |
| `S2-TAVILY-DEPTH-001` | C | Is shared-infra closure explicit enough? | Pass with grade C, not A. The ledger now cites `open_web_retrieval/src/open_web_retrieval/adapters/tavily.py`, local forwarding tests, and `open_web_retrieval/tests/test_adapters.py`. This remains a shared-infra closure row. |
| `S3-FRAME-MODEL-001` | A | Does the config test protect the Tyler A/B/C assignment? | Pass. `tests/test_tyler_v1_stage3_runtime.py::test_tyler_stage3_primary_config_matches_recovery_contract` asserts the current GPT/Gemini/Claude model order and reasoning-frame order. |
| `S3-MODEL-VERSION-001` | B | Is exact Gemini parity overclaimed? | Pass with grade B, not A. Closure rests on config, shared registry evidence, and runtime artifact `output/tyler_exact_model_version_switch_wave1_palantir/llm_observability.db`; it intentionally lacks a local pytest-only proof. |
| `S5-QUERY-ROLES-001` | A | Does Stage 5 test Tyler's literal query roles? | Pass. `tests/test_verify.py::test_build_tyler_verification_queries_matches_literal_query_roles` checks neutral, weaker-position, authoritative, and dated-query behavior. |
| `S6-PROMPT-VARS-001` | A | Does Stage 6 preserve Tyler's variable surface? | Pass. `tests/test_export.py::test_generate_tyler_synthesis_report_passes_tyler_stage6_prompt_variables` captures `claim_ledger`, `decision_critical_claim_ids`, and `user_response_for_dispute`. |
| `S6-MODEL-POLICY-001` | A | Does Stage 6 enforce non-dominant model policy? | Pass. `tests/test_export.py::test_generate_tyler_synthesis_report_uses_non_dominant_synthesis_model` asserts the selected synthesis model changes away from a dominant earlier-stage model. |
| `S6-GROUNDING-001` | A | Does grounding failure feed back into runtime, not just warning docs? | Pass. `tests/test_export.py::test_generate_tyler_synthesis_report_repairs_grounding_failure` forces an ungrounded first response and verifies a repair call produces a claim-cited recommendation. |
| `SC-PIPELINESTATE-001` | A | Does trace output use Tyler's canonical trace shape? | Pass. `tests/test_export.py::test_write_outputs_writes_tyler_pipeline_state_trace` exercises Tyler `PipelineState` serialization. |
| `DOC-*` rows | D | Are doc rows pretending to be Tyler runtime requirements? | Pass. Five local doc-governance rows now use explicit anchor exceptions, and `scripts/check_tyler_doc_drift.py` gates known stale active-doc claims. |
| `AMB-*` rows | D | Are Tyler ambiguities silently resolved? | Pass. Ambiguity rows cite conflicting Tyler lines and remain documented local interpretations rather than runtime parity claims. |

## Findings

No new blocking findings were found in this pass.

Dispositioned residual risks:

| Risk | Disposition |
|---|---|
| Raw Tyler packet remains ignored by git. | Still open as `GR-TYLER-TRACE-001`; derived ledger/matrices are tracked, but full reproduction from raw source remains clone-dependent. |
| `S3-MODEL-VERSION-001` has runtime-artifact/shared-infra evidence rather than local pytest proof. | Accepted at grade B; do not upgrade to A without a local deterministic assertion or a governed runtime-artifact checker. |
| `S2-TAVILY-DEPTH-001` relies on `open_web_retrieval` adapter behavior. | Accepted at grade C; shared-infra source and test references are explicit. |
| Active-doc drift detection is targeted, not semantic. | Accepted for this slice; it catches known high-risk stale claims and is backed by tests, but it is not a substitute for future semantic doc cleanup. |

## Verification

Commands run for this closure-review checkpoint:

```bash
python scripts/check_tyler_coverage.py --format json --fail-on-grade-f
python scripts/check_tyler_doc_drift.py --format json --fail-on-findings
python scripts/check_tyler_code_audit.py --format json --fail-on-findings
pytest tests/test_tyler_code_audit.py tests/test_tyler_doc_drift.py tests/test_tyler_coverage.py -q
make check
```
