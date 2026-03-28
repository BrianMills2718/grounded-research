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
| [depth_modes.md](depth_modes.md) | Completed | Standard/deep/thorough profiles shipped with deeper extraction, multi-round arbitration, and sectioned synthesis for long thorough-mode reports. Future depth work now requires a new benchmark-triggered plan. |
| [depth_modes_wave1_execution.md](depth_modes_wave1_execution.md) | Completed | Wave 1 depth continuation shipped: goal-driven evidence extraction in deep/thorough, multi-round arbitration, and a passing live deep collection smoke gate. |
| [sectioned_synthesis_wave1.md](sectioned_synthesis_wave1.md) | Completed | Benchmark-triggered export wave closed: the single-call `thorough` rerender failed the gate, sectioned synthesis was implemented, and the saved rerender now clears 11k words. |
| [thorough_benchmark_preservation_wave1.md](thorough_benchmark_preservation_wave1.md) | Completed | Fresh `thorough` UBI fixture benchmark completed; it regressed against both cached Perplexity and the prior dense-dedup anchor, but did not justify recent-first ranking, so the wave closed with recorded uncertainty and no new repo-local patch. |
| [tyler_literal_parity_refactor.md](tyler_literal_parity_refactor.md) | In Progress | Major contract migration to make Tyler's V1 schemas and prompts literal repo-local runtime surfaces rather than adapted references. Runtime Stage 1-6 migration and repo-local quality recovery are done; the remaining open work is explicit shared-infra boundary recording and any future benchmark-triggered divergence work. |
| [tyler_literal_parity_stage123_native.md](tyler_literal_parity_stage123_native.md) | Completed | Execution-ready remaining wave for literal Tyler parity completed: Tyler Stage 1-3 are now native runtime artifacts and Stage 4-6 prefer the persisted Tyler artifacts. |
| [tyler_literal_parity_benchmark_reanchor.md](tyler_literal_parity_benchmark_reanchor.md) | Completed | Post-migration benchmark gate for the fully Tyler-native runtime is complete: the runtime is stable end-to-end, but the tracked UBI rerun still regressed in usefulness after local mechanical fixes. |
| [tyler_literal_prompt_quality_recovery.md](tyler_literal_prompt_quality_recovery.md) | Completed | Repo-local Tyler-native prompt-quality recovery closed: Stage 3 role recovery and Stage 6 decision-field repair now beat cached Perplexity on the tracked UBI case and leave only a small, explicit gap to the dense-dedup anchor. |
| [tyler_stage3_model_role_recovery.md](tyler_stage3_model_role_recovery.md) | Completed | Gate-time execution slice under Tyler prompt-quality recovery: closest-available Stage 3 role parity removed DeepSeek from the primary path and recovered analyst density on the tracked UBI fixture. |
| [tyler_stage6_decision_guidance_recovery.md](tyler_stage6_decision_guidance_recovery.md) | Completed | Follow-up Stage 6 slice: underfilled decision fields now trigger a repair loop; the tracked UBI rerun fills tradeoffs and alternatives and remains slightly behind only the dense-dedup anchor. |
| [phase_b_source_quality.md](phase_b_source_quality.md) | Completed | Source quality scoring, evidence sufficiency, compression. |
| [phase_f_deferred_features.md](phase_f_deferred_features.md) | Completed | 6 deferred features promoted and implemented. |
| [TEMPLATE.md](TEMPLATE.md) | Template | Copy for new plans. |
