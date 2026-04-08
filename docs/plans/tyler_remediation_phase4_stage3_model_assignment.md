# Tyler Remediation Phase 4: Stage 3 Model Assignment

`docs/PLAN.md` remains the canonical repo-level plan. This file is the fourth
child implementation wave under `tyler_gap_remediation_wave1.md`.

**Status:** Completed
**Type:** implementation
**Priority:** Medium
**Blocked By:** `docs/plans/tyler_gap_remediation_wave1.md`
**Blocks:** truthful default Stage 3 frame-model mapping

---

## Goal

Patch `S3-FRAME-MODEL-001` in the default runtime config.

Tyler requires:

- Analyst A / `step_back_abstraction` → GPT-5.4
- Analyst B / `structured_decomposition` → Gemini
- Analyst C / `verification_first` → Claude Opus

The default config currently flips B and C.

---

## Scope

### In Scope

1. reorder default `analyst_models` in `config/config.yaml`
2. add a config-focused test proving the default frame-model order
3. document that `config/config.testing.yaml` remains intentionally cheap and
   non-literal

### Out of Scope

1. exact Gemini 3.1 Pro parity
2. changing the cheap testing profile
3. changing Stage 3 frames themselves

---

## Pre-Made Decisions

1. Only default/runtime-facing configs are patched to Tyler's requested order.
2. The testing config remains all-Gemini by design for cheap iteration.
3. `config/config.openrouter.yaml` already preserves the B/C structural order,
   so this wave does not change it.
4. The open shared-infra row for exact Gemini 3.1 Pro remains open after this wave.

---

## Success Criteria

Pass only if all of the following are true:

1. default config maps B → Gemini and C → Claude
2. OpenRouter default config matches the same order
3. tests prove the shipped default order
4. docs no longer treat the cheap testing profile as if it were Tyler-literal

## Outcome

Completed on 2026-04-08.

Implemented:

1. `config/config.yaml` now maps Analyst B to Gemini and Analyst C to Claude
   Opus, matching Tyler's requested default frame-model order.
2. The config-focused Stage 3 runtime test now validates the shipped default
   config directly instead of the cheap testing profile.
3. `config/config.testing.yaml` remains intentionally non-literal and cheap.

Verified with:

- `./.venv/bin/python -m pytest tests/test_tyler_v1_stage3_runtime.py -q`
