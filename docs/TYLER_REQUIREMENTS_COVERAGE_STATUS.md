# Tyler Requirements Coverage Status

> Provenance/status: Tyler review/provenance artifact. Preserve for audit.
> Some status claims may be superseded by the current machine-readable
> registry. For current status, cross-check `docs/MAINTAINER_START_HERE.md`,
> `docs/tyler_requirements.yaml`, and
> `docs/tyler_requirements_registry.json`.

> Sources consulted: `CLAUDE.md`; `README.md`;
> `docs/MAINTAINER_START_HERE.md`; `docs/PLAN.md`;
> `docs/CONCERNS.md`; `docs/TYLER_TRACEABILITY.md`;
> `docs/TYLER_AUDIT_QUALITY_STANDARD.md`;
> `docs/TYLER_INDEPENDENT_CLOSURE_REVIEW.md`;
> `docs/TYLER_SPEC_GAP_LEDGER.md`; `docs/TYLER_EXECUTION_STATUS.md`;
> `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md`;
> `docs/TYLER_SYSTEMATIC_REVIEW_MATRIX.md`;
> `docs/TYLER_V1_CURRENT_REPO_MAP.md`;
> `docs/plans/CLAUDE.md`;
> `docs/plans/maintainer_onboarding_cleanup_wave1.md`;
> `docs/TYLER_SOURCE_MANIFEST.md`; tracked raw Tyler packet in
> `2026_0325_tyler_feedback/`.
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

The directory remains listed in `.gitignore` to avoid accidental addition of
extra local feedback artifacts, but these four files are force-tracked and
verified by `docs/TYLER_SOURCE_MANIFEST.md` plus `make tyler-source-check`.

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
| Rows without source-code references | 1 |

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

What is now enforced:

- The structured registry is generated from the Markdown ledger and checked by
  `make check`.
- `docs/tyler_requirements.yaml` contains all 36 current Tyler rows with
  required evidence kinds by requirement class and is checked by `make check`.
- `make tyler-review` classifies all 36 rows by deterministic status,
  robustness status, and review mode; 15 grade-B/C/D rows are explicitly routed
  to human/LLM judgment rather than overclaimed as locally tested closure.
- Requirement-class evidence policy is implemented in
  `scripts/check_tyler_coverage.py` and enforced with
  `--fail-on-grade-f --fail-on-findings`.
- The coverage dashboard reports evidence grades, requirement classes, anchor
  status, and per-row findings.
- The fresh live-code audit checks non-doc Tyler rows for current
  implementation and verification evidence.
- Active-doc drift is scanned by `scripts/check_tyler_doc_drift.py`.
- Raw Tyler source files are tracked and hash-verified against
  `docs/TYLER_SOURCE_MANIFEST.md`.

What is still missing:

- A structured authoring source-of-truth for Tyler requirements. The current
  YAML and JSON files are generated snapshots checked against the Markdown
  ledger.
- A `trace_eval`-style runtime evidence checker once that shared library
  exists.
- A packaged frozen-output artifact story for clean worktrees. `make
  check-env` now explains missing local artifacts, but the artifacts themselves
  still live outside git.

### How much code and documentation is there?

Tracked repository counts from `git ls-files`:

| Area | Files | Lines |
|---|---:|---:|
| `src/**/*.py` | 23 | 7,684 |
| `engine.py` | 1 | 617 |
| `tests/**/*.py` | 33 | 7,851 |
| `scripts/**/*.py` | 17 | 3,377 |
| `prompts/` | 8 | 846 |
| `docs/**/*.md` | 114 | 16,667 |
| `docs/tyler_requirements_registry.json` | 1 | 1,475 |
| `docs/tyler_requirements.yaml` | 1 | 1,490 |
| all tracked Markdown | 131 | 23,528 |

The repo is documentation-heavy. That is useful for auditability, but only if
the active authority chain is small and stale docs are clearly marked.

## Current Authority Chain

Use this order until the traceability program inverts ownership and generates
the Markdown ledger from `docs/tyler_requirements.yaml`:

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
make tyler-doc-audit
make tyler-doc-audit-json
make tyler-code-audit
make tyler-code-audit-json
make tyler-source-check
make tyler-source-check-json
make tyler-registry-check
make tyler-registry-json
make tyler-registry-sync
make tyler-requirements-yaml-check
make tyler-requirements-yaml
make tyler-requirements-yaml-sync
make tyler-review
make tyler-review-json
make tyler-review-packets
make check
```

`make check` now fails on grade-F Tyler coverage rows, any coverage-quality
findings, and known active-doc drift findings. It also fails when non-doc Tyler
rows lack current implementation or verification evidence. The anchor policy is
closed for the current ledger: rows have either line-level Tyler anchors or
explicit doc-governance exceptions. The tracked raw Tyler source packet must
also match its manifest hashes and line counts. The generated structured
registry must also match the current ledger-derived read model.
`docs/tyler_requirements.yaml` must also match the current ledger-derived model
and satisfy its declared requirement-class evidence policy.
The identify-only Tyler review report must classify every requirement's proof
mode without treating artifact, shared-infra, doc, ambiguity, extension, or
watch evidence as local unit-test closure.

Quality standard:

- `docs/TYLER_AUDIT_QUALITY_STANDARD.md`

Current first-pass coverage-quality readout:

- 36 requirements
- 0 rows still need line-level Tyler source anchors or explicit exceptions
- 31 rows now have line-level Tyler source anchors
- 5 rows have explicit doc-governance anchor exceptions
- 0 active-doc drift findings across 41 active docs under the targeted current-state checker
- 24 non-doc/non-exception rows audited for current code evidence
- 0 current-code evidence gaps
- 4 raw Tyler source files tracked and hash-verified
- 36 rows exported in `docs/tyler_requirements_registry.json`
- first independent closure-review checkpoint recorded in
  `docs/TYLER_INDEPENDENT_CLOSURE_REVIEW.md`
- 21 grade `A`
- 2 grade `B`
- 1 grade `C`
- 12 grade `D`
- 0 grade `F`
- negative controls implemented for all seven audit-quality failure families

There are currently no grade-F rows or coverage-quality findings under the
strict coverage-quality policy. `EXT-SCHEMA-001` and `DOC-README-001` now grade `D`, which means
documented rather than strongly closed by runtime proof.
