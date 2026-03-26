# Implementation Plans

`docs/PLAN.md` is the canonical execution plan. This directory holds per-task plans.

## Plan Index

| Plan | Status | Summary |
|------|--------|---------|
| [v1_spec_alignment.md](v1_spec_alignment.md) | Reference analysis | Reconciliation memo: what differs between Tyler's V1 and the current repo, ordered by implementation value. |
| [v1_reasoning_quality_execution.md](v1_reasoning_quality_execution.md) | Completed | Wave 1 reasoning-quality stabilization: prompt hardening, claim extraction, dedup safeguards, anti-conformity, and anonymization. |
| [wave2_enumeration_grounding.md](wave2_enumeration_grounding.md) | Completed | Benchmark-driven follow-up for study/PDF retrieval, Claimify evidence anchoring, and dense-claim dedup on enumeration-heavy questions recovered the UBI benchmark. |
| [post_wave2_cleanup_hardening.md](post_wave2_cleanup_hardening.md) | Completed | Remaining internal hardening finished: dense canonicalization, prompt/config hygiene, trace construction cleanup, and sub-question evidence tagging. |
| [wave2_runtime_reliability.md](wave2_runtime_reliability.md) | Completed | Runtime reliability slice: run-local observability DBs, explicit request timeouts, and benchmark-safe completion policy. |
| [wave2_coverage_breadth.md](wave2_coverage_breadth.md) | Completed | Analyst coverage-target wiring and one under-coverage retry broadened the UBI claim set on rich bundles. |
| [wave2_report_synthesis_calibration.md](wave2_report_synthesis_calibration.md) | Completed | Export repair loops and stronger synthesis structure removed warnings/placeholders and recovered the UBI comparison. |
| [docs_authority_reconciliation.md](docs_authority_reconciliation.md) | Completed | CLAUDE, PLAN, ROADMAP, and the plan index now reflect the same current frontier. |
| [tyler_v1_followthrough.md](tyler_v1_followthrough.md) | Completed | Locks the Tyler V1 package as reference material, records intentional divergences, and closes the repo-local March 26 follow-through. |
| [depth_modes.md](depth_modes.md) | Partially implemented / deferred continuation | Standard/deep/thorough profiles shipped; deeper extraction/arbitration/synthesis extensions remain deferred. |
| [depth_modes_wave1_execution.md](depth_modes_wave1_execution.md) | In Progress | Next benchmark-driven depth wave: richer evidence extraction in deep/thorough, multi-round arbitration, then a benchmark/docs gate. |
| [phase_b_source_quality.md](phase_b_source_quality.md) | Completed | Source quality scoring, evidence sufficiency, compression. |
| [phase_f_deferred_features.md](phase_f_deferred_features.md) | Completed | 6 deferred features promoted and implemented. |
| [TEMPLATE.md](TEMPLATE.md) | Template | Copy for new plans. |
