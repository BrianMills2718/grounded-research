# Tyler Audit Quality Standard

> Provenance/status: Tyler review/provenance artifact. Preserve for audit.
> Some status claims may be superseded by the current machine-readable
> registry. For current status, cross-check `docs/MAINTAINER_START_HERE.md`,
> `docs/tyler_requirements.yaml`, and
> `docs/tyler_requirements_registry.json`.

> Sources consulted: `docs/TYLER_REQUIREMENTS_COVERAGE_STATUS.md`;
> `docs/TYLER_TRACEABILITY.md`; `docs/TYLER_SPEC_GAP_LEDGER.md`;
> `docs/TYLER_EXECUTION_STATUS.md`;
> `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md`;
> `docs/TYLER_SYSTEMATIC_REVIEW_MATRIX.md`;
> `docs/plans/tyler_requirements_traceability_program.md`;
> `docs/CONCERNS.md`.
>
> Status: required quality bar for the next Tyler traceability work.

## Purpose

The audit should not merely say "this row is closed." It should say what Tyler
required, where that requirement came from, what evidence closes it, how strong
that evidence is, and what would make the closure claim fail.

This standard exists to prevent three failure modes:

- closure by prose instead of evidence;
- link validity mistaken for behavioral verification;
- historical fix notes mistaken for current-code proof.

## Required Audit Properties

Every Tyler requirement row must eventually have:

1. **Line-level Tyler source anchor**: source file, heading, and line span.
2. **Requirement class**: schema, prompt, runtime behavior, provider behavior,
   model/config behavior, output artifact, doc/status, ambiguity, extension, or
   watch item.
3. **Closure status**: open, verified fixed, ambiguity documented, extension
   documented, operational watch, deferred shared-infra, or superseded stale
   doc.
4. **Evidence refs**: typed references to code, tests, prompts, docs, runtime
   artifacts, or shared-infra commands.
5. **Evidence grade**: strength of the closure claim.
6. **Adversarial notes**: what could falsify the row's closure claim.

## Evidence Grades

| Grade | Meaning | Minimum bar |
|---|---|---|
| A | Strong local closure | Tyler source anchor + current code/prompt/schema refs + local test or prompt-render test + checker validation |
| B | Runtime-artifact closure | Tyler source anchor + current code/config refs + reproducible command/config/artifact readout |
| C | Shared-infra closure | Tyler source anchor + local consumer ref + owner repo + shared verification command/artifact |
| D | Documented non-code closure | Tyler source anchor + explicit ambiguity/extension/doc-only rationale |
| F | Insufficient closure | Closed by prose, stale historical note, missing source anchor, or evidence kind does not match requirement class |

Rows may be legitimately grade `D`, but only when the requirement class allows
it. A runtime behavior row cannot close at `D`.

## Requirement-Class Evidence Policy

| Requirement class | Required evidence |
|---|---|
| `schema_contract` | Tyler line anchor, Pydantic model ref, schema/model test |
| `prompt_template` | Tyler line anchor, prompt template ref, prompt-render test |
| `runtime_behavior` | Tyler line anchor, function/module ref, unit or integration test |
| `provider_behavior` | Tyler line anchor, local forwarding test, shared-infra adapter test or artifact |
| `model_config` | Tyler line anchor, config ref, runtime observability artifact or config test |
| `output_artifact` | Tyler line anchor, writer/ref, fixture or runtime artifact assertion |
| `doc_status` | Tyler or ledger anchor, doc ref, doc-drift check |
| `ambiguity` | Conflicting Tyler anchors, local interpretation, no silent runtime assumption |
| `extension` | Extension rationale, non-conflict statement, owner |
| `operational_watch` | Watch threshold, monitoring/readout artifact, reopen rule |

## Two-Pass Extraction Standard

The raw Tyler packet should be processed in two passes:

1. **Normative extraction pass**: enumerate every statement that appears to
   impose behavior, schema, output, prompt, model, provider, or process
   requirements.
2. **Classification pass**: independently classify each extracted statement as
   requirement, context, ambiguity, extension/non-goal, or planning note.

Disagreements between the two passes become audit findings. They should not be
silently resolved by whichever interpretation is easier to implement.

## Adversarial Audit Lane

Every slice that closes or tightens Tyler traceability must include an
adversarial pass. The pass should try to find:

- rows marked closed but backed only by prose;
- tests that do not actually assert Tyler-specific behavior;
- source anchors that point to broad sections instead of exact requirements;
- current code paths that differ from historical fix notes;
- shared-infra claims without owner repo and verification command;
- runtime-artifact claims without command, config, and output path;
- active docs that contradict the structured registry.

Findings must be dispositioned as fixed, accepted with rationale, escalated, or
deferred to a named slice.

## Negative Controls

The checker should have fixture rows that are intentionally wrong, and tests
must prove they fail. Required negative controls:

1. closed runtime row with doc-only evidence;
2. closed schema row without a model test;
3. prompt row with a broken prompt-render test reference;
4. shared-infra row without `owner_repo`;
5. runtime-artifact row without command/config/artifact path;
6. Tyler requirement row without a line-level source anchor;
7. stale-doc row claiming closure status that conflicts with the registry.

Current implementation: `tests/meta/test_tyler_coverage.py` includes fixture-row
negative controls for all seven cases. These controls prove the non-strict
coverage checker can identify the failure families before those findings are
promoted into `make check` failures.

## Fresh-Code Audit Standard

Historical fix notes are provenance, not proof by themselves. A fresh-code audit
must verify current repo state by mapping each non-doc requirement to:

- current function, class, prompt, config, or writer;
- current test or runtime artifact;
- current failure mode if the requirement regresses.

The audit may use graph/code search, deterministic scans, and manual sampling,
but the final evidence must be recorded as structured refs.

## Runtime Artifact Standard

Rows closed by runtime artifacts must record:

- command used;
- config/profile used;
- required environment or model profile;
- output directory;
- specific artifact path;
- expected assertion or readout;
- whether the run is reproducible locally or depends on external provider state.

## Stop Line

Do not call a Tyler row strongly closed unless it has the evidence required by
its class and an evidence grade that licenses the claim being made.
