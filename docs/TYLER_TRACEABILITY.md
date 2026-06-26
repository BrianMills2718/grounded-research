# Tyler Traceability System

> Sources: `docs/TYLER_SPEC_GAP_LEDGER.md` ·
> `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md` ·
> `docs/TYLER_SYSTEMATIC_REVIEW_MATRIX.md` ·
> `docs/TYLER_EXECUTION_STATUS.md` ·
> `docs/TYLER_AUDIT_FAILURE_ANALYSIS.md` ·
> `docs/plans/maintainer_onboarding_cleanup_wave1.md`
>
> Status: first programmatic traceability spine.

## Purpose

Tyler compliance should be inspectable as data, not reconstructed from scattered
prose. The active source of truth remains the ledger/matrix documents, but the
repo now has a checker that parses them and answers:

- which Tyler requirement rows exist;
- which audit units and review lanes point at those rows;
- which code, prompt, doc, and test references are attached;
- whether referenced local files and pytest symbols still exist;
- which rows are closed, ambiguous, extension-only, or watch items.

## Commands

```bash
make tyler-traceability
make tyler-traceability-json
make tyler-coverage
make tyler-coverage-json
```

`make check` also runs the machine check in fail-on-broken-link mode.

## Current Readout

The current generated summary is:

| Metric | Count |
|---|---:|
| ledger rows | 36 |
| audit units | 108 |
| review lanes | 21 |
| broken local references | 0 |
| audit units pointing at missing ledger rows | 0 |
| review lanes pointing at missing ledger rows | 0 |
| verified rows without explicit test references | 1 |
| rows without source references | 1 |

Current non-closure rows:

- `STATUS-FRONTIER-RUNTIME-001` - operational watch item.
- `EXT-SCHEMA-001` - documented extension row.

Current evidence-quality flags:

- `S3-MODEL-VERSION-001` is verified from run artifacts and shared-infra
  evidence, but does not cite a local pytest test directly.
- `S2-TAVILY-DEPTH-001` is shared-infra-backed, so its strongest source/test
  evidence lives in `open_web_retrieval`.

These are not current broken links. They are prompts for future evidence-quality
improvement if the maintainer wants stricter closure criteria.

## Coverage Quality Readout

`make tyler-coverage` adds a coverage-quality view over the same ledger.
Grade-F rows and coverage-quality findings now fail `make check`.

Current first-pass readout:

| Metric | Count |
|---|---:|
| requirements | 36 |
| review needed | 0 |
| line-anchor pending | 0 |
| grade F | 0 |

Evidence grades:

| Grade | Rows |
|---|---:|
| A | 21 |
| B | 2 |
| C | 1 |
| D | 12 |

Requirement classes:

| Class | Rows |
|---|---:|
| ambiguity | 3 |
| doc_status | 8 |
| extension | 1 |
| model_config | 6 |
| operational_watch | 1 |
| prompt_template | 2 |
| provider_behavior | 2 |
| runtime_behavior | 6 |
| schema_contract | 7 |

Current grade-F rows under the calibrated policy: none. Current
coverage-quality findings: none.

`S2-QUERY-MODEL-001` and `S2-QUERY-VARIANTS-001` were reopened by the
coverage-quality pass and then fixed by restoring deterministic
string/orchestrator query templates in the live runtime. `EXT-SCHEMA-001` and
`DOC-README-001` now grade `D`, which means documented rather than strongly
closed by runtime proof. The source-anchor pass now leaves no pending rows:
31 rows cite line-level Tyler packet anchors, and five local doc-governance rows
carry explicit anchor exceptions rather than fake Tyler citations.

Negative controls are now covered in `tests/meta/test_tyler_coverage.py` for the
seven failure families listed in `docs/TYLER_AUDIT_QUALITY_STANDARD.md`, and
`make check` runs the calibrated `--fail-on-findings` gate.

## Artifact Roles

| Artifact | Role |
|---|---|
| `docs/TYLER_SPEC_GAP_LEDGER.md` | Requirement/gap ledger and current status by row. |
| `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md` | Coverage matrix over Tyler's source packet. |
| `docs/TYLER_SYSTEMATIC_REVIEW_MATRIX.md` | Review-lane tracker. |
| `docs/TYLER_INDEPENDENT_CLOSURE_REVIEW.md` | Adversarial closure-review checkpoint and residual-risk disposition. |
| `docs/TYLER_SOURCE_MANIFEST.md` | Raw Tyler packet line-count and hash manifest. |
| `docs/TYLER_REQUIREMENT_REVIEW_RUBRIC.md` | Success criteria and rubric for identify-only per-requirement review. |
| `docs/tyler_requirements.yaml` | Structured YAML requirements snapshot with class evidence policy. |
| `docs/tyler_requirements_registry.json` | Generated structured registry snapshot from the Markdown ledger. |
| `scripts/check_tyler_traceability.py` | Machine check and Markdown/JSON report. |
| `scripts/check_tyler_coverage.py` | Coverage-quality report with evidence grades and strict finding failures. |
| `scripts/check_tyler_doc_drift.py` | Active-doc drift report for known stale Tyler status claims. |
| `scripts/check_tyler_code_audit.py` | Current-code evidence audit for non-doc Tyler rows. |
| `scripts/check_tyler_source_manifest.py` | Raw Tyler source packet reproducibility check. |
| `scripts/generate_tyler_review_packets.py` | Identify-only review packets and deterministic status report for every Tyler row. |
| `scripts/sync_tyler_requirements_yaml.py` | Generate or check the structured YAML requirements snapshot. |
| `scripts/sync_tyler_registry.py` | Generate or check the structured registry snapshot. |
| `make tyler-traceability` | Human-readable report. |
| `make tyler-traceability-json` | Agent/tool-readable report. |
| `make tyler-coverage` | Human-readable audit-quality dashboard. |
| `make tyler-coverage-json` | Agent/tool-readable coverage-quality report. |
| `make tyler-doc-audit` | Human-readable active-doc drift report. |
| `make tyler-doc-audit-json` | Agent/tool-readable active-doc drift report. |
| `make tyler-code-audit` | Human-readable current-code evidence audit. |
| `make tyler-code-audit-json` | Agent/tool-readable current-code evidence audit. |
| `make tyler-source-check` | Human-readable raw Tyler source manifest check. |
| `make tyler-source-check-json` | Agent/tool-readable raw Tyler source manifest check. |
| `make tyler-registry-check` | Verify the tracked structured registry snapshot is current. |
| `make tyler-registry-json` | Emit the structured registry JSON to stdout. |
| `make tyler-registry-sync` | Regenerate the tracked structured registry snapshot. |
| `make tyler-requirements-yaml-check` | Verify the tracked YAML requirements snapshot is current and policy-clean. |
| `make tyler-requirements-yaml` | Emit the structured Tyler requirements YAML to stdout. |
| `make tyler-requirements-yaml-sync` | Regenerate the tracked structured Tyler requirements YAML. |
| `make tyler-review` | Summarize identify-only review status for every Tyler requirement. |
| `make tyler-review-json` | Emit identify-only Tyler review status as JSON. |
| `make tyler-review-packets` | Generate per-requirement review packets under `output/`. |

## Design Boundary

This is intentionally a one-way generated YAML/JSON structured surface from
existing authority docs, not a second manually edited ledger. The next
improvement should invert ownership so Markdown is generated from the YAML
source, but only after the current parser/report proves which fields are worth
governing.

## Next Improvements

1. Invert ownership so the Markdown ledger is generated from
   `docs/tyler_requirements.yaml`.
2. Add a `trace_eval`-style runtime evidence checker once that shared library
   exists.
3. Package frozen output artifacts for machines that do not have a populated
   local checkout. Local worktrees can now restore them with
   `make restore-frozen-outputs`.
