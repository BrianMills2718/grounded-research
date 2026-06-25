---
type: concept
status: proposed
updated: 2026-06-25
---

# MCP Evidence Discovery

MCP tools can broaden discovery for up-to-date research questions, but they
should remain outside the Tyler core until their outputs are normalized through
typed source-provider contracts.

## Available Discovery Surface

The current social-media MCP surface includes:

- GitHub repository search.
- arXiv search.
- Reddit search and user/post lookup.
- Medium search.
- Twitter/X search.
- Content fetch for candidate URLs.

This is valuable for questions where current practice matters, such as SOTA
retrieval methods, emerging libraries, practitioner discussions, and new papers.

## Boundary

MCP calls are candidate-source discovery. They are not evidence by themselves.
Before a result can influence a Tyler run, it needs:

- provider, query, timestamp, and URL provenance;
- normalization into the evidence/source schema;
- source quality and freshness scoring;
- deduplication against existing retrieved sources;
- trace inclusion with selection rationale.

## Acceptance Readouts For Future Work

- A frozen prompt set where MCP discovery improves source coverage without
  lowering source quality.
- A minimum evidence threshold for when discovery/search failure should fail
  loudly rather than produce a partial run.
- Trace records showing which MCP candidates were accepted or rejected.
- No direct MCP object leakage into report synthesis.
- No new source family bypassing Stage 2 or Stage 5 evidence gates.

## Depends On

- `docs/CONTRACTS.md`
- `docs/DOMAIN_MODEL.md`
- `docs/plans/maintainer_onboarding_cleanup_wave1.md`
- `docs/plans/llm_call_observability.md`
