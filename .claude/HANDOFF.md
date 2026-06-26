# grounded-research Handoff

Updated: 2026-06-26T10:05:58

## What This Project Is

`grounded-research` is an evidence-grounded research/adjudication pipeline. This branch is preparing an Inside-Success PR focused on Tyler's V1 requirements: making each requirement traceable, grading evidence honestly, enforcing deterministic local gates where possible, and routing non-deterministic or non-code rows to explicit review instead of pretending everything has a unit test.

## What Was Done This Session

- `8453b92` - Added the identify-only Tyler requirement review status harness.
- `988b076` - Added `docs/tyler_requirements.yaml` as the structured requirements snapshot generated from the current registry/ledger.
- `3ebff27` - Merged `inside-success/main` into `organize-tyler-maintainer-pr`; current branch is 0 behind and 40 commits ahead of Inside-Success main.
- Added `docs/TYLER_REQUIREMENT_REVIEW_RUBRIC.md`, `scripts/generate_tyler_review_packets.py`, and `tests/test_tyler_review_packets.py`.
- Added YAML sync/check machinery in `scripts/sync_tyler_requirements_yaml.py` and `tests/test_tyler_requirements_yaml.py`.
- Added Make targets: `tyler-requirements-yaml-check`, `tyler-requirements-yaml`, `tyler-requirements-yaml-sync`, `tyler-review`, `tyler-review-json`, and `tyler-review-packets`.
- Verified the branch with `make check PYTHON=/home/brian/projects/.venv/bin/python`: 230 passed, 6 skipped, Ruff clean, all Tyler gates clean.

## Current Tyler Status

The deterministic review report currently says:

| Metric | Count |
|---|---:|
| Requirements | 36 |
| Deterministic pass | 36 |
| Deterministic needs review | 0 |
| Policy findings | 0 |
| Robust local or prompt closures | 21 |
| Artifact-backed or operational-watch reviews | 2 |
| Shared-infra reviews | 1 |
| Accepted non-code reviews | 12 |
| Rows routed to `llm_or_human_judgment` | 15 |

Important wording: do not claim every Tyler row has a robust local unit test. The accurate claim is that every row has structured YAML, deterministic policy checks, a generated packet, a review mode, and an explicit status. Some rows are accepted doc/ambiguity/extension rows, some depend on artifacts or shared infra, and 15 B/C/D rows remain judgment-review rows.

## Active Source Files

| Path | Status | Notes |
|---|---|---|
| `docs/tyler_requirements.yaml` | committed source snapshot | Generated/checkable from the registry; update with `make tyler-requirements-yaml-sync`. |
| `docs/TYLER_REQUIREMENT_REVIEW_RUBRIC.md` | committed source | Defines success criteria and the judgment rubric. |
| `scripts/generate_tyler_review_packets.py` | committed source | Generates deterministic report and ignored packet artifacts. |
| `scripts/sync_tyler_requirements_yaml.py` | committed source | Builds/checks the YAML requirements snapshot. |
| `output/tyler_requirement_reviews/` | ignored generated artifact | Reproducible with `make tyler-review-packets`; do not edit directly. |
| `/home/brian/projects/inside-success/repos/grounded-research` | separate clone | Real Inside-Success private upstream clone; this worktree is under Brian's fork checkout. |

No important `/tmp/` ephemeral files are known.

## Build And Review Commands

```bash
cd /home/brian/projects/grounded-research/worktrees/organize-tyler-maintainer-pr
git status --short --branch
make check PYTHON=/home/brian/projects/.venv/bin/python
make tyler-review-json PYTHON=/home/brian/projects/.venv/bin/python
make tyler-review-packets PYTHON=/home/brian/projects/.venv/bin/python
```

Known caveat: `make check-strict` is not the current landing gate. It still exposes broader strict-mypy debt in the repo and should not be used as a blocker unless the next task is type-debt cleanup.

## Review Findings And Improvement Advice

### Finding 1: Judgment Review Is Identified, Not Collected

Severity: informational.

The current harness correctly routes 15 B/C/D rows to `llm_or_human_judgment`, but it does not yet collect structured reviewer verdicts. That is acceptable for the stated identify-only goal, but if Brian wants a stronger review package before PR, add an advisory result collector:

- Read packet Markdown from `output/tyler_requirement_reviews/packets`.
- Accept or produce structured JSON using the rubric schema in `docs/TYLER_REQUIREMENT_REVIEW_RUBRIC.md`.
- Write ignored results under `output/tyler_requirement_reviews/llm_results`.
- Keep live LLM calls outside `make check`; test only schema parsing and fixture aggregation.
- If using an LLM, use `llm_client` with `task=`, `trace_id=`, and `max_budget=`.

### Finding 2: PR Review Surface Is Large

Severity: informational.

The branch is 40 commits ahead of `inside-success/main` and changes 138 files. Tests are green, but a maintainer will need a tight PR description and possibly a commit map. The PR should clearly separate:

- Maintainer onboarding/doc cleanup.
- Tyler traceability and coverage gates.
- YAML requirements snapshot.
- Identify-only status review packets.

### Finding 3: Generated Outputs Are Ignored

Severity: informational.

The packet files under `output/tyler_requirement_reviews/` are ignored and reproducible. That is probably right, but the PR should mention how to regenerate them. Do not cite ignored packet files as review evidence unless the reviewer regenerates them or the PR includes the deterministic JSON summary in the description.

### Pass 1 Critical Review

No critical blocker found in the latest Tyler YAML/review-packet slice. No hardcoded secrets were found in the new Tyler machinery, no destructive operations were added, and the new checks fail loudly rather than silently falling back.

## Uncertainties

### U1: Should We Add The Judgment-Result Collector?

The user asked whether every Tyler requirement has robust tests, then clarified that identifying problems is enough and suggested LLM review packets with criteria and grading. The current branch satisfies deterministic identification and packet generation. It does not yet run or store LLM/human verdicts. Verify by asking whether the next desired deliverable is "PR now" or "add advisory judgment-result collector first."

### U2: Should The PR Be Trimmed Or Split?

The branch is coherent but large. If the maintainer prefers a smaller PR, split/squash may be useful. Do not rebase or force-push without explicit permission.

## Pending Work

### P1: Open Or Prepare The Inside-Success PR

Use target repo `Inside-Success/grounded-research`, base `main`, head `BrianMills2718:organize-tyler-maintainer-pr`. Include the verified command:

```bash
make check PYTHON=/home/brian/projects/.venv/bin/python
```

Include the key counts: 36 requirements, 36 deterministic pass, 0 deterministic needs review, 0 policy findings, 21 robust local/prompt closures, and 15 rows routed to judgment review.

### P2: Optional LLM/Human Judgment Collector

Add only if Brian wants the review to move beyond status identification. Keep it advisory and outside the default gate. The deterministic harness is already enough to identify which rows need judgment.

### P3: PR Description Accuracy

Avoid overstating. The honest summary is: every Tyler row is represented and classified; not every Tyler row should have a local unit test.

## Files That Must Not Be Edited Directly

- `output/tyler_requirement_reviews/*`: generated and ignored; regenerate with `make tyler-review-packets`.
- `docs/tyler_requirements.yaml`: generated/checkable snapshot; prefer `make tyler-requirements-yaml-sync`.
- `docs/tyler_requirements_registry.json`: generated/checkable registry; prefer `make tyler-registry-sync`.
- `docs/archive/*` and `docs/plans/archive/*`: historical archive surfaces; edit only when intentionally correcting stale references.

## Quick Sanity Checks

```bash
cd /home/brian/projects/grounded-research/worktrees/organize-tyler-maintainer-pr
git status --short --branch
git rev-list --left-right --count inside-success/main...HEAD
make check PYTHON=/home/brian/projects/.venv/bin/python
make tyler-review-json PYTHON=/home/brian/projects/.venv/bin/python
```

Expected:

- `git rev-list` prints `0	40` before the handoff commit, or `0	41` after committing this handoff.
- `make check` exits 0 with 230 passed and 6 skipped.
- `make tyler-review-json` reports 36 requirements, 0 deterministic needs-review rows, and 0 policy findings.
