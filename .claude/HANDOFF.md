# grounded-research Handoff

Updated: 2026-06-26T11:47:48-07:00

## What This Project Is

`grounded-research` is an evidence-grounded research/adjudication pipeline. The current branch stack prepares a maintainer-facing Inside-Success review of Tyler V1 requirement coverage: structured requirement data, deterministic status checks, generated review packets, strict typing, docstring hygiene, and clearer Tyler document provenance.

## What Was Done This Session

- `db24dbc` - Added the prior Tyler review handoff.
- `57c0326` - Cleaned the maintainer surface: Makefile help/targets and `docs/PLAN.md` current-authority framing.
- `f87b7f6` - Reduced low-risk mypy debt in config/compression/export/source-quality/Tyler adapter code.
- `390bc7d` - Finished strict typing and production/script docstring cleanup; added `scripts/check_docstrings.py`; made `make typecheck` pass.
- `c967c43` - Moved Tyler governance checker tests to `tests/meta/` and split product tests from meta-tests in Make targets.
- `325285f` - Added non-destructive Tyler doc provenance warnings, a Tyler document map in `docs/MAINTAINER_START_HERE.md`, and `scripts/check_tyler_doc_provenance.py`.

Draft PRs now open:

| PR | Base | Head | Purpose |
|---|---|---|---|
| #3 | `main` | `organize-tyler-maintainer-pr` | Tyler requirement status harness and review packets. |
| #4 | `organize-tyler-maintainer-pr` | `cleanup-maintainer-surface` | Maintainer surface cleanup. |
| #5 | `cleanup-maintainer-surface` | `typecheck-low-risk-cleanup` | Strict typing, docstrings, test organization, Tyler doc provenance. |

## Active Source Files

| Path | Status | Notes |
|---|---|---|
| `docs/tyler_requirements.yaml` | committed generated snapshot | Check with `make tyler-requirements-yaml-check`; sync with `make tyler-requirements-yaml-sync`. |
| `docs/tyler_requirements_registry.json` | committed generated snapshot | Check with `make tyler-registry-check`; sync with `make tyler-registry-sync`. |
| `scripts/check_docstrings.py` | committed checker | Enforces docstrings under `src/` and `scripts/`. |
| `scripts/check_tyler_doc_provenance.py` | committed checker | Ensures top-level `docs/TYLER*.md` files retain provenance/current-status warnings. |
| `tests/meta/` | committed tests | Governance checker tests separated from product tests. |
| `output/tyler_requirement_reviews/` | ignored generated artifact | Reproducible with `make tyler-review-packets`; do not edit directly. |

No important `/tmp/` ephemeral files are known.

## Build And Review Commands

```bash
cd /home/brian/projects/grounded-research/worktrees/organize-tyler-maintainer-pr
git status --short --branch
make check PYTHON=/home/brian/projects/.venv/bin/python
make check-strict PYTHON=/home/brian/projects/.venv/bin/python
python scripts/check_tyler_doc_provenance.py --format markdown --fail-on-findings
```

Latest verified strict result:

- product tests: `191 passed, 6 skipped`
- governance meta-tests: `42 passed`
- Ruff clean
- docstring gate clean
- Tyler gates clean
- provenance gate clean
- strict mypy: `Success: no issues found in 23 source files`

## Uncertainties

No implementation blocker remains. The remaining choices are review/process choices:

### PR Readiness

The PRs are still draft. Decide whether to mark them ready now or wait until Mikias/Milkias confirms `Inside-Success/grounded-research` is the right up-to-date repo/branch target.

### Slack Contact

The best Slack target found earlier was `#sd-github-tyler`, tagging Mikias/Milkias. Use the concise message Brian requested, not an over-explained one.

## Pending Work

### P1: Reviewer Communication

Send the Slack note once Brian wants it. Suggested shape:

```text
hey @Mikias, is https://github.com/Inside-Success/grounded-research the up-to-date repo for the research engine? if so, I did some cleanup and submitted a PR here: https://github.com/Inside-Success/grounded-research/pull/3

I made a machine-readable list of Tyler's requirements/specs and linked each row to the current tests/status checks so we can see the current state without rereading all the docs. Overview: 36 requirements represented; deterministic policy checks are clean; review packets are generated; rows that need human/LLM judgment are explicitly marked instead of being overclaimed as local-test closures.
```

### P2: Optional Judgment Collector

Only add this if explicitly requested. The current harness identifies review modes/status; it does not collect final human/LLM verdict JSON for the 15 B/C/D rows.

## Files That Must Not Be Edited Directly

- `output/tyler_requirement_reviews/*`: generated and ignored; regenerate with `make tyler-review-packets`.
- `docs/tyler_requirements.yaml`: generated/checkable snapshot; prefer `make tyler-requirements-yaml-sync`.
- `docs/tyler_requirements_registry.json`: generated/checkable registry; prefer `make tyler-registry-sync`.
- Top-level `docs/TYLER*.md`: preserve in place. Do not archive/move Tyler-provenance docs; add provenance warnings and cross-check the registry when claims disagree.

## Quick Sanity Checks

```bash
git status --short --branch
make check-strict PYTHON=/home/brian/projects/.venv/bin/python
python scripts/check_tyler_doc_provenance.py --format markdown --fail-on-findings
```

Expected:

- clean worktree on `typecheck-low-risk-cleanup`
- strict check exits 0
- provenance check reports 16 docs and 0 findings
