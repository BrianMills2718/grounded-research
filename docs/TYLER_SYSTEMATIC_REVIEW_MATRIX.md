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
| R2 | Stage 2 | query diversification prompt and typed query plans | static review + stage runtime test | `S2-QUERY-MODEL-001` | done | ledger only |
| R3 | Stage 2 | provider routing by query type | behavior check or runtime test | `S2-ROUTING-001` | done | ledger only |
| R4 | Stage 2 | quality scoring pipeline | static review + deterministic test | `S2-QUALITY-001` | done | ledger only |
| R5 | Stage 2 | Tavily depth behavior from consumer boundary | request-body or adapter verification | `S2-TAVILY-DEPTH-001` | done | ledger only |
| R6 | Stage 2 | Exa retrieval instruction/control behavior | request-body or adapter verification | `S2-EXA-CONTROLS-001` | done | ledger only |
| R7 | Stage 3 | frame/model assignment | static review + config/runtime test | `S3-FRAME-MODEL-001` | done | ledger only |
| R8 | Stage 3 | exact Tyler model-version parity | config review + shared ownership review | `S3-MODEL-VERSION-001` | active | shared remediation or closure note |
| R9 | Stage 4 | analyst-order randomization | behavior test | `S4-ORDER-RANDOMIZATION-001` | done | ledger only |
| R10 | Stage 5 | query roles | runtime test | `S5-QUERY-ROLES-001` | done | ledger only |
| R11 | Stage 5 | search parameter execution | runtime/provider verification | `S5-SEARCH-PARAMS-001` | done | ledger only |
| R12 | Stage 5 | round cap and arbitration ordering | behavior test | `S5-ROUND-CAP-001`, `S5-ORDER-RANDOMIZATION-001` | done | ledger only |
| R13 | Stage 6a | post-Stage-5 steering sequencing | behavior test | `S6A-STEERING-001` | done | ledger only |
| R14 | Stage 6b | source propagation and compaction | behavior test | `S6-EVIDENCE-CONTEXT-001`, `S6-COMPACTION-001` | done | ledger only |
| R15 | Stage 6b | non-dominant synthesis model policy | static review + runtime test | `S6-MODEL-POLICY-001` | done | ledger only |
| R16 | Shared runtime | frontier literal runtime reliability | fixture evidence + policy review | `STATUS-FRONTIER-RUNTIME-001` | active | policy + possible shared follow-through |
| R17 | Docs | active status surfaces do not outrun ledger | doc review | `docs/TYLER_EXECUTION_STATUS.md`, `docs/TYLER_SHARED_INFRA_OWNERSHIP.md`, `docs/plans/CLAUDE.md` | active | doc corrections |
| R18 | Governance | review process still follows ledger-first rule | doc/process review | `docs/TYLER_AUDIT_FAILURE_ANALYSIS.md`, `docs/plans/tyler_audit_governance_wave1.md` | pending | governance update if needed |

## Immediate Open Lanes

The currently open lanes are deliberately narrow:

1. `R8` exact model-version parity
2. `R16` frontier runtime/model-policy lane
3. `R17` ongoing doc truthfulness check
4. `R18` governance hardening only if this review exposes another process gap

## Review Rule

No lane moves to `done` unless the supporting evidence is reflected in the
ledger or the relevant status doc in the same change set.
