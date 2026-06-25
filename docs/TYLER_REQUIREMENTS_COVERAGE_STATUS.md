# Tyler Requirements Coverage Status

> Sources consulted: `CLAUDE.md`; `README.md`;
> `docs/MAINTAINER_START_HERE.md`; `docs/PLAN.md`;
> `docs/CONCERNS.md`; `docs/TYLER_TRACEABILITY.md`;
> `docs/TYLER_AUDIT_QUALITY_STANDARD.md`;
> `docs/TYLER_SPEC_GAP_LEDGER.md`; `docs/TYLER_EXECUTION_STATUS.md`;
> `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md`;
> `docs/TYLER_SYSTEMATIC_REVIEW_MATRIX.md`;
> `docs/TYLER_V1_CURRENT_REPO_MAP.md`;
> `docs/plans/CLAUDE.md`;
> `docs/plans/maintainer_onboarding_cleanup_wave1.md`;
> raw Tyler packet in ignored local directory `2026_0325_tyler_feedback/`.
>
> Status: current-state checkpoint. This is not a PR-readiness claim.

## Purpose

This document captures the thing maintainers must not lose track of: Tyler
requirements need to be traceable from source text to code, tests, docs, prompt
templates, runtime artifacts, and shared-infra evidence. The current branch has
a first programmatic read model, but it does not yet prove full requirement
coverage at the evidence standard we want.

## Direct Answers

### Did we find Tyler's requirements?

Yes, locally. The raw Tyler packet is in `2026_0325_tyler_feedback/`:

| Source file | Lines |
|---|---:|
| `1. V1_Build_Plan_Step_By_Step.md` | 248 |
| `2. V1_DESIGN.md` | 347 |
| `3. V1_SCHEMAS.md` | 619 |
| `4. V1_PROMPTS.md` | 1,163 |
| Total | 2,377 |

Important caveat: that directory is currently ignored by `.gitignore`, so a
fresh clone cannot independently regenerate the audit from the raw Tyler packet.
That is a reproducibility gap.

### Is there a test for every Tyler requirement?

No. The current checker proves local references and matrix cross-links are not
broken. It does not prove every Tyler requirement has a local pytest test.

Current generated traceability readout:

| Metric | Count |
|---|---:|
| Ledger rows | 36 |
| Full-spec audit units | 108 |
| Systematic review lanes | 21 |
| Broken local references | 0 |
| Audit units pointing at missing ledger IDs | 0 |
| Review lanes pointing at missing ledger IDs | 0 |
| Verified rows without explicit local test references | 1 |
| Rows without source-code references | 2 |

Known evidence-quality flags:

- `S3-MODEL-VERSION-001` is verified from config, shared-infra registry work,
  and runtime artifacts, but lacks an explicit local pytest reference.
- `S2-TAVILY-DEPTH-001` is shared-infra-backed; strongest adapter evidence
  lives in `open_web_retrieval`.
- `DOC-README-001` is a documentation row and does not need source-code
  evidence.

The next system must distinguish evidence kinds:

- local unit test
- local integration/runtime test
- prompt-render test
- static code reference
- runtime artifact
- shared-infra test or artifact
- doc-only evidence
- Tyler-internal ambiguity record

### Did we audit the codebase?

Partially, and enough to have useful structure, but not enough to declare the
high-level work done.

What exists:

- The full-spec audit matrix has 108 source-section audit units.
- The systematic review matrix has 21 review lanes.
- The gap ledger has 36 rows with current status, owner, evidence, and next
  action.
- `scripts/check_tyler_traceability.py` can validate references and emit JSON or
  Markdown.

What is still missing:

- A structured source-of-truth for Tyler requirements. The source of truth is
  still Markdown tables, parsed by convention.
- A policy that says which requirement classes require which evidence kinds.
- A quality standard that is enforced by code, not only described in docs.
- A generated coverage dashboard that shows pass/fail by evidence class.
- A fresh live-code audit that traces each requirement to concrete functions,
  tests, and runtime artifacts using a repeatable process.
- Reconciliation of stale or conflicting active docs. For example,
  `docs/TYLER_V1_CURRENT_REPO_MAP.md` still says several Tyler-required items
  remain, while the newer ledger/status docs say audited local implementation
  rows are closed except watch, extension, and Tyler-ambiguity rows.

### How much code and documentation is there?

Tracked repository counts from `git ls-files`:

| Area | Files | Lines |
|---|---:|---:|
| `src/**/*.py` | 23 | 7,696 |
| `engine.py` | 1 | 617 |
| `tests/**/*.py` | 25 | 7,252 |
| `scripts/**/*.py` | 8 | 1,522 |
| `prompts/` | 9 | 898 |
| `docs/**/*.md` | 108 | 15,480 |
| all tracked Markdown | 121 | 19,963 |

The repo is documentation-heavy. That is useful for auditability, but only if
the active authority chain is small and stale docs are clearly marked.

## Current Authority Chain

Use this order until the traceability program replaces it with structured data:

1. Raw Tyler packet in `2026_0325_tyler_feedback/`.
2. `docs/TYLER_SPEC_GAP_LEDGER.md`.
3. `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md`.
4. `docs/TYLER_SYSTEMATIC_REVIEW_MATRIX.md`.
5. `docs/TYLER_EXECUTION_STATUS.md`.
6. Generated report from `make tyler-traceability-json`.

When these disagree, do not infer. Record the disagreement as a concern and
reconcile the canonical artifact.

## Current Stop Line

Do not describe the repository as PR-ready on Tyler requirements coverage until
all of these are true:

1. The raw Tyler packet is tracked or copied into a controlled tracked source
   location, or there is an explicit documented reason it cannot be tracked.
2. Tyler requirement rows have a structured source-of-truth, not only Markdown
   tables.
3. Every requirement row declares the evidence kind required for closure.
4. Every requirement row has a line-level Tyler source anchor or explicit
   exception.
5. Every closed row has an evidence grade that matches the audit quality
   standard.
6. The checker fails when a row marked closed lacks its required evidence kind.
7. Negative-control fixtures prove the checker catches false closure cases.
8. Active docs that contradict the ledger are reconciled or marked superseded.
9. A fresh codebase audit has been run and recorded against the structured rows.
10. Shared-infra rows name the owning repo, artifact, and verification command.

## Commands

Current commands:

```bash
make tyler-traceability
make tyler-traceability-json
make tyler-coverage
make tyler-coverage-json
make check
```

Still missing:

```bash
make tyler-doc-audit
```

Quality standard:

- `docs/TYLER_AUDIT_QUALITY_STANDARD.md`

Current first-pass coverage-quality readout:

- 36 requirements
- 36 rows still need line-level Tyler source anchors
- 19 grade `A`
- 2 grade `B`
- 1 grade `C`
- 10 grade `D`
- 4 grade `F`
- negative controls implemented for all seven audit-quality failure families

The grade-F rows are audit-evidence gaps, not newly discovered runtime
regressions: `S2-QUERY-MODEL-001`, `S2-QUERY-VARIANTS-001`,
`EXT-SCHEMA-001`, and `DOC-README-001`.
