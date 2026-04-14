# Tyler PipelineState Trace Contract Reprojection

This directory exists to leave behind one fresh success-path `trace.json`
artifact under the post-fix Tyler trace contract without requiring a new
frontier-model run.

Provenance:

- source run: `output/tyler_exact_model_version_switch_wave1_palantir/`
- source trace shape: historical repo-local runtime `PipelineState`
- reprojection writer: `src/grounded_research/export.py` `write_tyler_trace()`
- generated on: `2026-04-14`

Why this exists:

- the final local Tyler remediation row was `SC-PIPELINESTATE-001`
- that fix changed `trace.json` from repo-local runtime shape to Tyler's
  canonical `PipelineState` contract
- this artifact is a durable success-path example written by the fixed trace
  projection code

Expected top-level keys in `trace.json`:

- `query_id`
- `original_query`
- `started_at`
- `current_stage`
- `stage_1_result`
- `stage_2_result`
- `stage_3_alias_mapping`
- `stage_3_results`
- `stage_4_result`
- `stage_5_result`
- `stage_5_skipped`
- `stage_6_user_input`
- `stage_6_result`
- `completed_at`
- `errors`
- `total_cost_usd`
