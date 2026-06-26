# Maintainer Onboarding Cleanup Wave 1

## Status

In progress.

## Mission

Prepare a reviewable maintainer-facing requirements-coverage surface without
changing Tyler V1 runtime behavior. This is a prerequisite to any later PR
readiness claim, not a claim that the branch is ready. The end state should let
the current implementer quickly answer:

- What is the current Tyler source of truth?
- Which Tyler requirement rows link to code, prompt, test, doc, and runtime
  evidence?
- Which docs are active versus historical?
- Which local gates are expected to pass?
- Where should future evidence-source and MCP work plug in?

The active follow-on plan is
`docs/plans/tyler_requirements_traceability_program.md`.

## Modality Diagnosis

This is hybrid work.

- Deductive: documentation authority, plan indexing, local gate behavior, and
  source-of-truth ordering can be specified directly from existing repo docs.
  Tyler requirement traceability can start as a read model over the existing
  ledger/matrix docs because the audit rows already have stable IDs.
- Exploratory: future MCP/source discovery should remain a planned extension
  because source quality, rate limits, auth, and Tyler-fit need runtime readouts
  before changing the core pipeline.

## Scope

In scope:

- Make `make check` truthful and locally runnable.
- Keep strict typecheck visible as debt instead of hiding failures.
- Move completed Tyler wave plans into the archive.
- Add maintainer start-here documentation.
- Add a small Karpathy-style wiki spine for durable concepts.
- Add a programmatic Tyler traceability check that links requirement rows to
  code, prompt, test, doc, and shared-infra evidence references.
- Document which local infrastructure can help future project work.
- Document MCP/social-source discovery as an extension path, not Tyler core.

Out of scope:

- Changing Tyler Stage 1-6 behavior.
- Reopening closed Tyler gap-ledger rows.
- Adding new runtime MCP integrations.
- Rewriting historical plans or generated output artifacts.

## Acceptance Criteria

- `make check` passes locally.
- `make typecheck` remains callable and its current failure is documented.
- Active plan index contains only live/reference/template plans.
- Completed plan files moved with git history preserved.
- Maintainer documentation identifies the Tyler authority chain.
- Wiki pages have clear page types and source provenance.
- `make tyler-traceability` produces a human-readable Tyler requirement report.
- `make tyler-traceability-json` produces parseable JSON for agents/tools.
- `make check` fails on broken Tyler ledger/matrix links.
- The traceability readout reports current open rows and evidence-quality flags.
- Local infrastructure opportunities are named with boundaries.
- MCP evidence discovery is documented behind typed provider boundaries.

## Failure Modes

| Failure | Diagnostic | Response |
|---------|------------|----------|
| Archived plan treated as active requirement | Compare against `docs/TYLER_SPEC_GAP_LEDGER.md` and `docs/TYLER_EXECUTION_STATUS.md` | Update index wording; do not reopen work from title alone |
| Cleanup changes runtime behavior | Review diff under `src/` and run tests | Revert or isolate behavior change unless explicitly required |
| MCP plan bypasses Tyler contracts | Check proposed flow against EvidencePackage/EvidenceBundle boundaries | Keep MCP output as discovery input until typed normalization exists |
| Gates are misleading | Run `make check`, `make typecheck`, and link checks | Document non-green strict gates explicitly |
| Traceability becomes a second source of truth | Compare generated report fields against ledger/matrix docs | Keep the checker as a read model until the ledger is promoted to structured data |
| Shared-infra evidence is mistaken for local test coverage | Inspect reference kind in the traceability report | Mark `llm_client`, `open_web_retrieval`, and `prompt_eval` evidence as external/shared |

## Implementation Slices

1. Gate hygiene: make the default local check pass without false success.
2. Plan surface cleanup: archive completed waves and rewrite the plan index.
3. Maintainer orientation: add start-here and wiki pages.
4. Tyler traceability read model: parse ledger/matrix docs, validate references,
   and expose Markdown/JSON reports.
5. Local infrastructure alignment: document where shared libraries, future
   `trace_eval`, and MCP discovery can help.
6. Verification checkpoint: run gates, commit, push, and summarize residual
   risks without claiming PR readiness.

Current correction: do not frame this branch as PR-ready until the structured
Tyler requirements coverage program closes its stop lines.
