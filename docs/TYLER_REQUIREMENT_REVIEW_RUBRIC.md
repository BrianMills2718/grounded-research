# Tyler Requirement Review Rubric

This rubric defines success criteria for identifying the status of every Tyler
requirement. This is an identify-only review layer: it classifies closure
strength and suspected gaps, but it does not fix findings.

## Success Criteria

A Tyler requirement status is robustly determined when all of the following are
true:

1. The requirement appears in `docs/tyler_requirements.yaml`.
2. The requirement has a generated review packet.
3. The requirement has a deterministic review record with:
   - `deterministic_status`
   - `robustness_status`
   - `review_modes`
   - `findings`
   - `recommended_next_action`
4. The deterministic review record distinguishes local test proof from
   artifact, shared-infra, doc-only, ambiguity, extension, or watch evidence.
5. Non-code rows are not mislabeled as locally unit-tested closure.
6. Any grade `B`, `C`, or `D` row is explicitly marked as needing judgment,
   external confirmation, artifact review, or accepted non-code review.
7. The summary accounts for all current Tyler rows exactly once.

## Robustness Status Values

| Status | Meaning |
|---|---|
| `robust_local_closure` | Current local implementation evidence and local test evidence support the row. |
| `prompt_template_closure` | Prompt template plus prompt/runtime test evidence support the row. |
| `artifact_backed_review` | Runtime artifact evidence supports the row, but reviewer should inspect artifact freshness and command reproducibility. |
| `shared_infra_review` | Closure depends on shared infrastructure evidence outside this repo. |
| `accepted_doc_status` | Row governs documentation/status truthfulness and is covered by doc-drift/policy checks. |
| `accepted_ambiguity` | Tyler packet ambiguity is documented; no silent runtime assumption should be hidden. |
| `accepted_extension` | Row is a documented extension/non-conflict claim rather than direct Tyler implementation. |
| `operational_watch` | Row is closed as a watch item with a threshold/reopen rule. |
| `needs_review` | Deterministic checks found a gap or could not classify the row safely. |

## Review Modes

Review modes are evidence channels, not all rows need every mode:

- `unit_or_integration_test`
- `prompt_render_test`
- `runtime_artifact_check`
- `shared_infra_evidence`
- `doc_drift_check`
- `metadata_policy_check`
- `ambiguity_review`
- `extension_review`
- `operational_watch_review`
- `llm_or_human_judgment`

## LLM/Human Review Rubric

When a row needs judgment, review the generated packet using these criteria:

| Criterion | Question |
|---|---|
| Source fidelity | Does the closure claim match Tyler's source requirement or declared exception? |
| Evidence relevance | Do cited files, tests, docs, artifacts, or shared-infra refs actually prove the row? |
| Evidence freshness | Is the claim based on current code/artifacts rather than historical prose alone? |
| Closure class fit | Is the requirement class and evidence grade appropriate? |
| Test strength | Is the row locally tested where local testing is the right proof type? |
| Residual risk | What would falsify the closure claim? |

Suggested structured verdict:

```json
{
  "requirement_id": "S2-QUERY-MODEL-001",
  "verdict": "pass | needs_review | fail",
  "scores": {
    "source_fidelity": 1,
    "evidence_relevance": 1,
    "evidence_freshness": 1,
    "closure_class_fit": 1,
    "test_strength": 1
  },
  "findings": [],
  "residual_risk": "",
  "recommended_next_action": ""
}
```
