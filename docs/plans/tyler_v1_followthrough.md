# Tyler V1 Follow-Through

**Status:** Completed
**Purpose:** Close the documentation and planning gap after reviewing Tyler's
March 26 V1 package without confusing that package for the current shipped
state of `grounded-research`.

## Decisions Pre-Made

1. Tyler's V1 package is retained as reference material, not adopted as the
   canonical contract for this repo.
2. Provider-parity work (Tavily/Exa adapters, provider-specific semantics) is
   shared infrastructure and belongs in `open_web_retrieval`.
3. Gemini structured-output quality concerns are shared-infrastructure
   evaluation work and belong in `llm_client` / `prompt_eval`.
4. Current repo enums and report contracts are not renamed just for vocabulary
   parity with Tyler V1.
5. Repo-local work for this follow-through is documentation and planning
   closure, not a new implementation wave.

## Acceptance Criteria

This follow-through is complete only if:

1. The repo contains one concise note mapping Tyler V1 to the current repo and
   distinguishing intentional divergences from real gaps.
2. `CLAUDE.md` and `AGENTS.md` make the shared-infra boundary explicit for
   provider adapters and the proven `research_v3` bundle path.
3. `CLAUDE.md` and `AGENTS.md` strengthen the continuous-execution rule so
   agents do not stop after one patch when a plan is still open.
4. The plan index reflects this closure work.
5. Any remaining Tyler-derived gaps are recorded either as shared-infra
   follow-ups or future-alignment candidates, not left ambiguous in chat only.

## Failure Modes

| Failure mode | What it looks like | Mitigation |
|---|---|---|
| Tyler package mistaken for current repo audit | agents try to patch current enums/prompts blindly | keep the divergence map as the first reference |
| Shared-infra drift back into the project | Tavily/Exa clients added locally | lock the provider boundary in `CLAUDE.md` |
| Autonomy drift | agents pause after one patch with open plan work | strengthen continuous-execution language in canonical guidance |
| Research-v3 handoff forgotten | imported-bundle path treated as hypothetical | document the proven `--fixture` path explicitly |

## Implemented

1. Added `docs/TYLER_V1_CURRENT_REPO_MAP.md`
2. Updated `CLAUDE.md`
3. Updated `AGENTS.md`
4. Updated the plan index and canonical execution plan
5. Added a notebook review artifact for this follow-through

## Residual External Follow-Ups

These are real, but not repo-local:

1. `open_web_retrieval`: Tavily/Exa provider parity and provider semantics
2. `llm_client` / `prompt_eval`: Gemini structured-output quality evaluation

## Verification

- `CLAUDE.md` and `AGENTS.md` match exactly
- plan index references this completed follow-through
- no repo-local Tyler ambiguity remains about provider ownership or the
  `research_v3` handoff path
