# Tyler Remediation Phase 7: Stage 2 Exa Retrieval Instruction

`docs/TYLER_SPEC_GAP_LEDGER.md` is the canonical evidence source. This child
wave closes the remaining local part of the Stage 2 Exa control row now that
shared infra supports a generic retrieval-instruction field.

**Status:** Completed
**Type:** implementation
**Priority:** High
**Blocked By:** `open_web_retrieval` Plan #16 complete
**Blocks:** truthful closure of the remaining Stage 2 Exa parity row

---

## Goal

Teach the live Stage 2 Exa semantic path to pass a generic retrieval
instruction through the shared contract so `grounded-research` can express
Tyler's source-preference guidance instead of relying only on query text and
corpus/category hints.

---

## Ledger Rows

- `S2-EXA-CONTROLS-001`

---

## Scope

### In Scope

1. extend the local Stage 2 Exa query-plan surface with one optional
   `retrieval_instruction`
2. populate that field for Stage 2 semantic Exa queries from Tyler-style source
   preference guidance
3. pass the field through `search_web_exa()` into shared `SearchQuery`
4. add tests proving the instruction reaches the shared wrapper call
5. update the ledger/status docs if the row is fully closed

### Out of Scope

- new shared-infra work in `open_web_retrieval`
- Stage 5 changes
- broader retrieval redesign

---

## Pre-Made Decisions

1. reuse the shared generic field name `retrieval_instruction`; do not add a
   local Exa-specific name
2. keep the instruction short and deterministic, derived from Stage 1
   `search_guidance`
3. only Exa semantic queries carry this field
4. if `search_guidance` offers no useful preference signal, leave the field
   empty rather than inventing one

---

## Success Criteria

1. Stage 2 Exa semantic query plans can carry `retrieval_instruction`
2. `search_web_exa()` forwards that field into shared `SearchQuery`
3. tests prove the local Exa path passes the instruction through
4. `S2-EXA-CONTROLS-001` can be updated based on actual code evidence

---

## Outcome

Completed on 2026-04-08.

Landed behavior:

1. extended `Stage2QueryPlan` with optional `retrieval_instruction`
2. derived deterministic Exa retrieval guidance from Stage 1 `search_guidance`
3. passed the instruction through `search_web_exa()` into shared `SearchQuery`
4. closed the remaining local half of `S2-EXA-CONTROLS-001`

## Verification Results

- `./.venv/bin/python -m py_compile src/grounded_research/models.py src/grounded_research/tools/web_search.py src/grounded_research/collect.py tests/test_collect.py tests/test_web_search.py tests/test_tyler_v1_stage2_runtime.py`
- `./.venv/bin/python -m pytest tests/test_tyler_v1_stage2_runtime.py tests/test_collect.py tests/test_web_search.py -q`
