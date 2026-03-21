# ADR 0002: Approved External Reuse Strategy

## Status

Accepted

## Date

2026-03-21

## Context

`grounded-research` is deliberately scoped as an adjudication-first layer rather
than a new end-to-end research pipeline.

That means the project should reuse mature upstream systems where reuse reduces
implementation load without undermining:

- `llm_client` as the required LLM runtime surface
- the local trace and typed-state model
- the claim-ledger-first architecture
- the adjudication-first project boundary

Several external repos are relevant to the design space:

- STORM / `knowledge-storm`
- GPT Researcher
- LangGraph
- AutoGen
- DebateLLM
- MedAgents
- MetaGPT
- Free-MAD / Exchange-of-Thought style repos and papers

The decision needed is not whether these repos are interesting. The decision is
which ones are appropriate to leverage directly in this repo and which should
remain inspiration, benchmarks, or optional upstream inputs.

## Decision

### Approved For Direct Leverage

Use these as optional upstream providers, baselines, or adapter targets:

- **STORM / `knowledge-storm`**
- **GPT Researcher**

Approved usage modes:

- benchmark baseline in `Phase -1`
- optional upstream evidence or report producer
- adapter target for imported evidence bundles or intermediate artifacts

### Approved Conditionally

Use this only if the implementation proves it is needed:

- **LangGraph**

Approved usage mode:

- orchestration substrate only if resumable execution, interrupts, or
  long-running stateful workflow become real requirements that exceed a simple
  local orchestrator

### Not Approved As Core Dependencies For v1

Do not make these foundational dependencies of `grounded-research` v1:

- **AutoGen**
- **DebateLLM**
- **MedAgents**
- **MetaGPT**
- **Free-MAD**
- **Exchange-of-Thought** implementations

These may still be used for:

- design inspiration
- evaluation baselines
- prompt or protocol ideas

But they should not define the core runtime architecture of this repo.

## Consequences

### Positive

- avoids hand-rolling upstream research capabilities that already exist
- preserves the adjudication-first boundary
- keeps the core of this repo small and novel
- gives `Phase -1` concrete comparison targets
- leaves room for later orchestration upgrades without overcommitting early

### Negative

- imported upstream artifacts may require adapter work
- baseline comparisons may expose format mismatch and provenance mismatch
- some popular multi-agent frameworks remain intentionally unused despite their
  feature breadth

## Follow-On Rules

1. `Phase -1` should compare at least one local/manual evidence path and one
   external upstream path when practical.
2. External engines are upstream inputs or baselines, not the adjudication
   layer itself.
3. Any adapter into STORM or GPT Researcher must preserve provenance,
   timestamps, and source identity.
4. Adopting LangGraph as a required runtime dependency needs a new ADR.
