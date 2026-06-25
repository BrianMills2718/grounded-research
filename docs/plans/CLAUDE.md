# Implementation Plans

`docs/PLAN.md` is the canonical execution plan. This directory holds active,
reference, and template plans only. Completed Tyler remediation waves are kept
in `docs/plans/archive/` for auditability, not as the maintainer's working set.

## Maintainer Rule

Before opening a new implementation wave, read the authority documents in this
order:

1. `docs/TYLER_SPEC_GAP_LEDGER.md`
2. `docs/TYLER_EXECUTION_STATUS.md`
3. `docs/ROADMAP.md`
4. `docs/CONCERNS.md`
5. the relevant active/reference plan below

Do not infer open Tyler work from archived plan titles. The ledger and execution
status are the source of truth.

## Active And Reference Plans

| Plan | Status | Purpose |
|------|--------|---------|
| [v1_spec_alignment.md](v1_spec_alignment.md) | Reference analysis | Reconciliation memo for Tyler V1 versus the repository. Use only with the current gap ledger. |
| [v1_gap_closure.md](v1_gap_closure.md) | Planned/reference | Gap-closure framing for V1 work; revalidate against the ledger before executing. |
| [post_audit_maintainability_wave1.md](post_audit_maintainability_wave1.md) | Planned | Strictly limited maintainability work that supports Tyler remediation without changing the runtime contract. |
| [maintainer_onboarding_cleanup_wave1.md](maintainer_onboarding_cleanup_wave1.md) | In progress | Organization and onboarding PR for plan hygiene, local gates, maintainer docs, and MCP extension guidance. |
| [llm_call_observability.md](llm_call_observability.md) | Partial/reference | Observability plan for LLM/tool calls and shared infrastructure alignment. |
| [TEMPLATE.md](TEMPLATE.md) | Template | Copy for new implementation plans. |

## Historical Plans

Completed plans live in [archive/](archive/). They are useful for provenance and
regression archaeology, but they are not current requirements. When a historical
plan conflicts with the Tyler gap ledger or execution status, trust the current
ledger/status pair.

## Adding A New Plan

1. Start from [TEMPLATE.md](TEMPLATE.md).
2. State the Tyler requirement or maintainer concern that justifies the work.
3. Define acceptance criteria before implementation.
4. Add the plan to the active table only while it is executable.
5. Move it to `archive/` after completion and update this index.
