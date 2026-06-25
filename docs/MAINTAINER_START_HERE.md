# Maintainer Start Here

This repository is a Tyler V1 compliance project first and a general research
system second. When documents disagree, use the authority chain below instead
of inferring requirements from historical plans or old delivery summaries.

## Authority Chain

1. `docs/TYLER_SPEC_GAP_LEDGER.md` - canonical code-vs-spec evidence ledger.
2. `docs/TYLER_REQUIREMENTS_COVERAGE_STATUS.md` - current requirements coverage
   status and stop lines.
3. `docs/TYLER_AUDIT_QUALITY_STANDARD.md` - evidence grades and closure bar.
4. `docs/TYLER_EXECUTION_STATUS.md` - current implementation status.
5. `docs/ROADMAP.md` - forward-looking gates and stop lines.
6. `docs/CONCERNS.md` - open risk register.
7. `docs/PLAN.md` and `docs/plans/CLAUDE.md` - current execution framing.

Archived plans in `docs/plans/archive/` are provenance. They explain how the
repo got here; they do not create active requirements by themselves.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e ../llm_client
pip install -e ../open_web_retrieval
pip install -e ../data_contracts
```

The default search path currently uses Tavily through shared retrieval. Configure
provider keys in your normal secret environment before running raw-question
research flows.

`llm_client` and `open_web_retrieval` are required shared local infrastructure.
`data_contracts` is recommended for boundary registration; local tests can still
run without it because the live verification boundary has a fail-loud import
fallback for the decorator only.

## Verification Gates

```bash
make check
```

`make check` is the maintainer gate for this branch: tests plus Ruff lint.

```bash
make typecheck
```

`make typecheck` is intentionally still exposed and currently tracks strict mypy
debt. Do not hide this with `|| true`; fix it in a dedicated type-hardening wave
when it becomes the active plan.

## Runtime Stop Lines

- Do not describe this branch as PR-ready for Tyler requirements work until the
  structured coverage plan has closed its stop lines.
- Do not change Tyler Stage 1-6 behavior as part of documentation cleanup.
- Do not reopen a closed Tyler gap without updating the evidence ledger.
- Do not route new sources directly into synthesis; normalize them through the
  Tyler evidence contracts first.
- Do not treat old benchmark summaries as stronger than current frozen-eval docs.

## MCP Evidence Discovery

The social-media MCP is useful as a discovery layer for current public-source
signals: GitHub repositories, arXiv papers, Reddit discussions, Medium posts,
Twitter/X posts, and fetched content. It should not be wired directly into the
Tyler runtime without a plan.

The safe extension shape is:

1. MCP/tool call discovers candidate sources.
2. A source-provider adapter normalizes candidates into typed evidence records.
3. Existing evidence quality, freshness, provenance, and Tyler Stage 2/5 gates
   decide whether those sources can influence a run.
4. The trace records provider, query, timestamp, source URL, and selection reason.

See `docs/wiki/concepts/mcp-evidence-discovery.md` for the design boundary.

## Sources Consulted

- `CLAUDE.md`
- `README.md`
- `docs/PLAN.md`
- `docs/ROADMAP.md`
- `docs/CONCERNS.md`
- `docs/ARTIFACTS.md`
- `docs/TYLER_SPEC_GAP_LEDGER.md`
- `docs/TYLER_EXECUTION_STATUS.md`
- `docs/TYLER_V1_CURRENT_REPO_MAP.md`
- `docs/plans/CLAUDE.md`
- `docs/TYLER_CROSS_REPO_HANDOFF_2026_04_14.md`
