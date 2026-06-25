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
| rows without source references | 2 |

Current non-closure rows:

- `STATUS-FRONTIER-RUNTIME-001` - operational watch item.
- `EXT-SCHEMA-001` - documented extension row.

Current evidence-quality flags:

- `S3-MODEL-VERSION-001` is verified from run artifacts and shared-infra
  evidence, but does not cite a local pytest test directly.
- `S2-TAVILY-DEPTH-001` is shared-infra-backed, so its strongest source/test
  evidence lives in `open_web_retrieval`.
- `DOC-README-001` is a doc-status row and does not need source-code evidence.

These are not current broken links. They are prompts for future evidence-quality
improvement if the maintainer wants stricter closure criteria.

## Artifact Roles

| Artifact | Role |
|---|---|
| `docs/TYLER_SPEC_GAP_LEDGER.md` | Requirement/gap ledger and current status by row. |
| `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md` | Coverage matrix over Tyler's source packet. |
| `docs/TYLER_SYSTEMATIC_REVIEW_MATRIX.md` | Review-lane tracker. |
| `scripts/check_tyler_traceability.py` | Machine check and Markdown/JSON report. |
| `make tyler-traceability` | Human-readable report. |
| `make tyler-traceability-json` | Agent/tool-readable report. |

## Design Boundary

This is intentionally a read model over existing authority docs, not a new
second ledger. The next improvement should be schema-backed editing of the
ledger, but only after the current parser/report proves which fields are worth
governing.

## Next Improvements

1. Promote the ledger rows into a YAML or JSON source file and generate the
   Markdown ledger from it.
2. Add per-row evidence kinds: static code, unit test, integration test, runtime
   artifact, shared-infra evidence, doc-only.
3. Add owners for shared-infra evidence rows so `open_web_retrieval`,
   `llm_client`, and `prompt_eval` references are explicit rather than prose.
4. Add a `trace_eval`-style runtime evidence checker once that shared library
   exists.
