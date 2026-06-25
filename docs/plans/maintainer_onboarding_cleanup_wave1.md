# Maintainer Onboarding Cleanup Wave 1

## Status

In progress.

## Mission

Prepare a reviewable maintainer-facing PR that organizes the repository without
changing Tyler V1 runtime behavior. The end state should let the current
implementer quickly answer:

- What is the current Tyler source of truth?
- Which docs are active versus historical?
- Which local gates are expected to pass?
- Where should future evidence-source and MCP work plug in?

## Modality Diagnosis

This is hybrid work.

- Deductive: documentation authority, plan indexing, local gate behavior, and
  source-of-truth ordering can be specified directly from existing repo docs.
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
- MCP evidence discovery is documented behind typed provider boundaries.

## Failure Modes

| Failure | Diagnostic | Response |
|---------|------------|----------|
| Archived plan treated as active requirement | Compare against `docs/TYLER_SPEC_GAP_LEDGER.md` and `docs/TYLER_EXECUTION_STATUS.md` | Update index wording; do not reopen work from title alone |
| Cleanup changes runtime behavior | Review diff under `src/` and run tests | Revert or isolate behavior change unless explicitly required |
| MCP plan bypasses Tyler contracts | Check proposed flow against EvidencePackage/EvidenceBundle boundaries | Keep MCP output as discovery input until typed normalization exists |
| Gates are misleading | Run `make check`, `make typecheck`, and link checks | Document non-green strict gates explicitly |

## Implementation Slices

1. Gate hygiene: make the default local check pass without false success.
2. Plan surface cleanup: archive completed waves and rewrite the plan index.
3. Maintainer orientation: add start-here and wiki pages.
4. Extension documentation: record MCP evidence-source boundaries.
5. Verification and PR: run gates, commit, push, and summarize residual risks.
