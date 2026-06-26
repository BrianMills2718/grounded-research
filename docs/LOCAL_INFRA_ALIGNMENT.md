# Local Infrastructure Alignment

> Sources: `docs/TYLER_TRACEABILITY.md` · `docs/TYLER_CROSS_REPO_HANDOFF_2026_04_14.md` ·
> `docs/TYLER_SHARED_INFRA_OWNERSHIP.md` · `docs/MAINTAINER_START_HERE.md` ·
> `docs/wiki/concepts/mcp-evidence-discovery.md` · repo setup in `README.md`
>
> Status: first maintainer map.

## Useful Local Infrastructure

| Local capability | How it can help this project | Boundary |
|---|---|---|
| `data_contracts` | Register Tyler boundary schemas and make cross-project contract drift visible. | Use for boundary registration; do not make the runtime depend on registry availability for local tests. |
| `open_web_retrieval` | Owns web search/fetch provider behavior, including Tavily and Exa controls. | Tyler Stage 2/5 should consume typed provider controls, not provider-specific ad hoc code. |
| `llm_client` | Owns model registry, structured-output calls, observability DBs, and cost/error evidence. | Tyler model/runtime evidence should come from real observability rows, not estimates. |
| `prompt_eval` | Owns frozen Tyler-vs-legacy comparisons and prompt/model evaluation. | Use when a prompt/model/export change needs regression evidence; do not rerun broad evals for docs-only cleanup. |
| `enforced-planning` | Captures the methodology learned from the Tyler audit: ledger-first spec work, behavior-vs-structure evidence, and no status overclaim. | Upstream generalized governance there after this repo's traceability spine stabilizes. |
| `trace_eval` (planned) | Natural home for runtime trace assertions: event order, value propagation, model usage, and artifact completeness. | Until it exists, keep runtime evidence checks local and explicit. |
| social-media MCP | Discovery layer for GitHub, arXiv, Reddit, Medium, Twitter/X, and fetched candidate content. | Discovery only; normalize through typed evidence-provider contracts before Stage 2/5 can rely on it. |

## Best Next Use

The highest-leverage local-infra move is not adding more retrieval sources yet.
It is turning Tyler traceability into a governed data flow:

```text
Tyler source packet
  -> audit units
  -> ledger rows
  -> code/prompt/test/runtime evidence references
  -> generated docs and checks
```

The current PR starts with a read model over Markdown. The next PR should either:

- promote the ledger to YAML/JSON and generate the Markdown docs, or
- add a narrow `data_contracts` boundary around the traceability report so other
  projects can consume it consistently.

## MCP Extension Path

The social-media MCP is valuable for up-to-date research questions, but it
should enter this project behind a source-provider seam:

1. MCP returns candidate sources.
2. Adapter normalizes candidates into evidence/source records.
3. Stage 2/5 quality and freshness scoring decides whether they matter.
4. Traceability records provider/query/timestamp/selection reason.

Do not wire MCP results directly into synthesis.
