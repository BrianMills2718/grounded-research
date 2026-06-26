# Capability Decomposition

Last updated: 2026-06-26

## Purpose

Repo-local source of record for what `grounded-research` owns as a claim arbitration and
evidence-evaluation layer, what it exports to downstream consumers, and what it should not absorb.

## Role

`grounded-research` owns:

- multi-model dispute arbitration (Tyler V1 Stage 5 arbitration pipeline)
- evidence-backed claim evaluation and adjudication

It does not own:

- LLM execution (stays in llm_client)
- web retrieval (stays in open_web_retrieval)
- prompt evaluation framework (stays in prompt_eval)

## Capability Ledger

| Capability | Owner | Class | Notes |
|---|---|---|---|
| Multi-model claim arbitration | grounded-research | application | Tyler V1 multi-model arbitration for dispute resolution |

## Known Consumers

- Human researchers (adjudication outputs from investigation pipelines)

## References

- `src/grounded_research/verify.py` — Stage 5 arbitration implementation
- `docs/TYLER_SHARED_INFRA_OWNERSHIP.md` — ownership surface documentation
- `docs/METHODOLOGY.md` — adjudication methodology
