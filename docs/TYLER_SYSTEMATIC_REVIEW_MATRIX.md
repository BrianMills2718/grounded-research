# Tyler Systematic Review Matrix

This file is the compact execution tracker for the current systematic Tyler
review.

The ledger is the canonical findings surface:

- `docs/TYLER_SPEC_GAP_LEDGER.md`

This matrix exists to make the review itself mechanical:

- what lane is being reviewed,
- what evidence is required,
- whether the lane is already closed,
- and where the result should land.

## Status Key

- `done` — reviewed and consistent with the ledger
- `active` — current review lane
- `pending` — not yet re-reviewed in this wave

## Review Lanes

| review_id | scope | review focus | evidence required | current source of truth | status | next artifact |
|---|---|---|---|---|---|---|
| R1 | Stage 1 | prompt, schema, no-validation runtime path | static review + stage runtime test | `S1-VALIDATION-001` | done | ledger only |
| R2 | Stage 2 | query diversification mechanism and variant family | static review + stage runtime test | `S2-QUERY-MODEL-001`, `S2-QUERY-VARIANTS-001`, `DOC-S2-QUERY-002` | done | ledger only |
| R3 | Stage 2 | provider routing by query type | behavior check or runtime test | `S2-ROUTING-001` | done | ledger only |
| R4 | Stage 2 | quality scoring pipeline | static review + deterministic test | `S2-QUALITY-001` | done | ledger only |
| R5 | Stage 2 | Tavily depth behavior from consumer boundary | request-body or adapter verification | `S2-TAVILY-DEPTH-001` | done | ledger only |
| R6 | Stage 2 | Exa retrieval instruction/control behavior | request-body or adapter verification | `S2-EXA-CONTROLS-001` | done | ledger only |
| R7 | Stage 3 | frame/model assignment and role-label interpretation | static review + config/runtime test | `S3-FRAME-MODEL-001`, `AMB-S3-FRAME-001` | done | ledger only |
| R8 | Stage 3 | exact Tyler model-version parity | config review + shared ownership review | `S3-MODEL-VERSION-001` | done | ledger only |
| R9 | Stage 4 | analyst-order randomization | behavior test | `S4-ORDER-RANDOMIZATION-001` | done | ledger only |
| R10 | Stage 5 | query roles | runtime test | `S5-QUERY-ROLES-001` | done | ledger only |
| R11 | Stage 5 | search parameter execution | runtime/provider verification | `S5-SEARCH-PARAMS-001` | done | ledger only |
| R12 | Stage 5 | round cap and arbitration ordering | behavior test | `S5-ROUND-CAP-001`, `S5-ORDER-RANDOMIZATION-001` | done | ledger only |
| R13 | Stage 6a | post-Stage-5 steering sequencing | behavior test | `S6A-STEERING-001` | done | ledger only |
| R14 | Stage 6b | source propagation and compaction | behavior test | `S6-EVIDENCE-CONTEXT-001`, `S6-COMPACTION-001` | done | ledger only |
| R15 | Stage 6b | non-dominant synthesis model policy | static review + runtime test | `S6-MODEL-POLICY-001` | done | ledger only |
| R16 | Shared runtime | frontier literal runtime reliability | fixture evidence + policy review | `STATUS-FRONTIER-RUNTIME-001` | done | ledger only |
| R17 | Docs | active status surfaces do not outrun ledger | doc review | `docs/TYLER_EXECUTION_STATUS.md`, `docs/TYLER_SHARED_INFRA_OWNERSHIP.md`, `docs/plans/CLAUDE.md`, `README.md`, `docs/FEATURE_STATUS.md`, `docs/ROADMAP.md` | done | ledger only |
| R18 | Governance | review process still follows ledger-first rule | doc/process review | `docs/TYLER_AUDIT_FAILURE_ANALYSIS.md`, `docs/plans/tyler_audit_governance_wave1.md` | done | ledger only |
| R19 | Stage 6 | grounding reject-and-retry plus remaining final-report validation rules | behavior check + runtime path review | `S6-GROUNDING-001`, `S6-VALIDATION-COVERAGE-001` | done | ledger only |
| R20 | Schemas packet | pipeline-state trace parity plus remaining schema packet skip/trace semantics | static review + runtime trace + schema tests | `SC-PIPELINESTATE-001`, `AMB-S6A-STATUS-001`, `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md` | done | ledger + audit matrix |
| R21 | Prompts packet | remaining prompt-template literalness and prompt-side design constraints | prompt render + static review | `S6-PROMPT-VARS-001`, `S5-S6-DATASTRUCT-001`, `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md` | done | ledger + audit matrix |

## Immediate Open Lanes

The exhaustive Tyler packet audit currently has no active review lanes and no
remaining active local implementation rows.

The only non-closure item left is:

1. `STATUS-FRONTIER-RUNTIME-001`
   - operational watch item under the documented policy threshold
   - not an active implementation blocker

## Review Rule

No lane moves to `done` unless the supporting evidence is reflected in the
ledger or the relevant status doc in the same change set.
