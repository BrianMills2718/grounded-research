# Grounded Research Wiki Rules

This directory is a Karpathy-style concept wiki for the repository. It explains
durable ideas and navigational structure; it is not the source of truth for
Tyler compliance status.

## Page Types

- `index`: entrypoint and map of the wiki.
- `concept`: stable idea or design boundary.
- `source`: source packet or authority summary.
- `log`: dated change log for wiki maintenance.

## Rules

- Every concept/source page has YAML frontmatter with `type`, `status`, and
  `updated`.
- Each page lists the repo documents it depends on.
- Requirement claims link back to the Tyler ledger/status docs.
- MCP/source-expansion pages describe extension boundaries only unless a live
  implementation plan exists.
