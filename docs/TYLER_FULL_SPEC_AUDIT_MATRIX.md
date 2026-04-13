# Tyler Full Spec Audit Matrix

This file is the exhaustive coverage tracker for auditing Tyler's four
canonical V1 source files against the live `grounded-research` codebase.

Canonical findings still live in:

- `docs/TYLER_SPEC_GAP_LEDGER.md`

This file answers a different question:

- has every Tyler source section been audited?

## Status Key

- `pending` — not yet audited
- `in_progress` — currently being audited
- `audited_no_gap` — audited, no gap recorded
- `audited_gap_recorded` — audited, gap(s) recorded in the ledger
- `audited_context_only` — audited, source section is contextual/narrative only
- `blocked_shared` — audited, real issue exists but owner is shared infra

## Rows

| audit_unit_id | source_doc | source_section | unit_kind | tyler_audit_intent | evidence_kind | coverage_status | ledger_rows | notes |
|---|---|---|---|---|---|---|---|---|
| BP-INTRO-001 | `1. V1_Build_Plan_Step_By_Step.md` | `# V1 Build Plan — Step by Step` | `context_only` | overall execution intent and phase decomposition | static review | audited_context_only | none | root source summary only; normative requirements are audited in child rows |
| BP-S1-001 | `1. V1_Build_Plan_Step_By_Step.md` | `## Stage 1 — Intake & Decomposition` | `stage_rule` | Stage 1 runtime behavior, outputs, and limits | static + runtime | audited_gap_recorded | `S1-VALIDATION-001`, `S3-MODEL-VERSION-001` | Stage 1 no-validation and exact Gemini parity were audited; both rows now have ledger evidence |
| BP-S2-001 | `1. V1_Build_Plan_Step_By_Step.md` | `## Stage 2 — Broad Retrieval & Evidence Normalization` | `stage_rule` | Stage 2 retrieval, routing, scoring, normalization | static + runtime | audited_gap_recorded | `S2-QUERY-MODEL-001`, `S2-QUERY-VARIANTS-001`, `S2-ROUTING-001`, `S2-QUALITY-001`, `S2-TAVILY-DEPTH-001`, `S2-EXA-CONTROLS-001` | Exhaustive audit reopened Stage 2 query generation: Tyler packet says orchestrator string templates and a different variant family than the current live query-plan surface |
| BP-S3-001 | `1. V1_Build_Plan_Step_By_Step.md` | `## Stage 3 — Independent Candidate Generation` | `stage_rule` | Stage 3 model roles, quality floor, outputs | static + runtime | audited_gap_recorded | `S3-FRAME-MODEL-001`, `S3-MODEL-VERSION-001`, `STATUS-FRONTIER-RUNTIME-001`, `AMB-S3-FRAME-001` | Local frame/model mapping fix is landed, but the Tyler packet itself is internally inconsistent about B/C frame assignment |
| BP-S4-001 | `1. V1_Build_Plan_Step_By_Step.md` | `## Stage 4 — Claim Extraction & Dispute Localization` | `stage_rule` | Stage 4 extraction, localization, ordering | static + runtime | audited_gap_recorded | `S4-ORDER-RANDOMIZATION-001` | Stage 4 primacy-bias mitigation required a real local fix |
| BP-S5-001 | `1. V1_Build_Plan_Step_By_Step.md` | `## Stage 5 — Targeted Verification & Arbitration` | `stage_rule` | Stage 5 query roles, search params, arbitration, caps | static + runtime | audited_gap_recorded | `S5-QUERY-ROLES-001`, `S5-SEARCH-PARAMS-001`, `S5-ROUND-CAP-001`, `S5-ORDER-RANDOMIZATION-001` | Stage 5 core runtime rows were previously fixed and verified; no new Build Plan-only contradiction found in this tranche |
| BP-S6A-001 | `1. V1_Build_Plan_Step_By_Step.md` | `## Stage 6a — User-Steering Interrupt` | `branch_or_skip_rule` | Stage 6a trigger, queue selection, surfaced disputes | static + runtime | audited_gap_recorded | `S6A-STEERING-001` | Sequencing and queue-selection gap was real and is already in the ledger |
| BP-S6B-001 | `1. V1_Build_Plan_Step_By_Step.md` | `## Stage 6b — Synthesis & Final Report` | `output_contract` | Stage 6 synthesis, evidence use, output requirements | static + runtime | audited_gap_recorded | `S6-EVIDENCE-CONTEXT-001`, `S6-COMPACTION-001`, `S6-GROUNDING-001`, `S6-VALIDATION-COVERAGE-001`, `S6-MODEL-POLICY-001` | Stage 6 synthesis rows are mostly fixed, but exhaustive audit reopened grounding and final-report validation coverage requirements |
| BP-S6B-TIERA-001 | `1. V1_Build_Plan_Step_By_Step.md` | `### Tier A: Executive (what the user reads first)` | `output_contract` | executive report content contract | static + render | pending | none |  |
| BP-S6B-TIERB-001 | `1. V1_Build_Plan_Step_By_Step.md` | `### Tier B: Analytical (what the user reads for understanding)` | `output_contract` | analytical report content contract | static + render | pending | none |  |
| BP-S6B-TIERC-001 | `1. V1_Build_Plan_Step_By_Step.md` | `### Tier C: Evidentiary (what the user reads for verification)` | `output_contract` | evidentiary report content contract | static + render | pending | none |  |
| BP-TRACE-001 | `1. V1_Build_Plan_Step_By_Step.md` | `### Trace File (separate from report)` | `output_contract` | trace file fields and behavior | static + artifact | audited_no_gap | none | `engine.py` writes `trace.json` on success and failure; `write_outputs()` and the exception handler both materialize the artifact |
| BP-CCR-001 | `1. V1_Build_Plan_Step_By_Step.md` | `## Cross-Cutting Requirements` | `cross_cutting_rule` | umbrella cross-cutting rules | static review | audited_no_gap | none | umbrella row only; audited through child cross-cutting rows below |
| BP-CCR-REASONING-001 | `1. V1_Build_Plan_Step_By_Step.md` | `### Reasoning field` | `cross_cutting_rule` | reasoning field protocol | static review | audited_no_gap | none | `StageSummary`, `AnalysisObject`, `ArbitrationAssessment`, and `SynthesisReport` all include `reasoning`; the separate Stage 2 `Finding` conflict is tracked under schema/prompt ambiguity rows |
| BP-CCR-FALLBACK-001 | `1. V1_Build_Plan_Step_By_Step.md` | `### Fallback logic` | `cross_cutting_rule` | fallback behavior constraints | static + runtime | audited_no_gap | none | Build Plan fallback chains for Stage 1, Stage 4, Stage 6b, and Stage 3 min-success are present; extra fallback surfaces are additive extensions, not contradictions |
| BP-CCR-PARTIALTRACE-001 | `1. V1_Build_Plan_Step_By_Step.md` | `### Partial trace on abort` | `cross_cutting_rule` | abort-time trace preservation | static + failure-path | audited_no_gap | none | `engine.py` exception path writes partial `trace.json` before re-raising |
| BP-CCR-ANON-001 | `1. V1_Build_Plan_Step_By_Step.md` | `### Anonymization` | `cross_cutting_rule` | anonymization requirements | static + runtime | audited_no_gap | none | `engine.py` scrubs Stage 3 outputs with `scrub_tyler_analysis_object()` and tests cover self-identification removal |
| BP-CCR-ANTICONFORMITY-001 | `1. V1_Build_Plan_Step_By_Step.md` | `### Anti-conformity` | `cross_cutting_rule` | anti-conformity enforcement | static + runtime | audited_no_gap | none | `ClaimStatusUpdate.basis_for_change` restricts status changes to Tyler's allowed bases; verification tests cover the enforcement layer |
| BP-LIMITATIONS-001 | `1. V1_Build_Plan_Step_By_Step.md` | `## Known Limitations` | `context_only` | accepted limitations and non-goals | static review | audited_context_only | none | context/accepted-tradeoff section; normative requirements are audited in other rows |
| DS-WHAT-001 | `2. V1_DESIGN.md` | `## What This Is` | `context_only` | product framing and scope intent | static review | pending | none |  |
| DS-WHY-001 | `2. V1_DESIGN.md` | `### Why It Exists` | `context_only` | rationale only unless normative constraints appear | static review | pending | none |  |
| DS-SCOPE-001 | `2. V1_DESIGN.md` | `### Scope` | `cross_cutting_rule` | formal scope constraints | static review | pending | none |  |
| DS-NONGOALS-001 | `2. V1_DESIGN.md` | `### Non-Goals (architecture constraints, not just positioning)` | `cross_cutting_rule` | architecture prohibitions | static review | pending | none |  |
| DS-THEORY-001 | `2. V1_DESIGN.md` | `## Operating Theory` | `context_only` | theory of operation | static review | pending | none |  |
| DS-CONSTRAINTS-001 | `2. V1_DESIGN.md` | `## Design Constraints` | `cross_cutting_rule` | design constraints with normative effect | static review | pending | none | split if needed |
| DS-PIPE-S1-001 | `2. V1_DESIGN.md` | `### Stage 1 — Intake & Decomposition` | `stage_rule` | design-level Stage 1 constraints | static + runtime | pending | none |  |
| DS-PIPE-S2-001 | `2. V1_DESIGN.md` | `### Stage 2 — Broad Retrieval & Evidence Normalization` | `stage_rule` | design-level Stage 2 constraints | static + runtime | pending | none |  |
| DS-PIPE-S3-001 | `2. V1_DESIGN.md` | `### Stage 3 — Independent Candidate Generation` | `stage_rule` | design-level Stage 3 constraints | static + runtime | pending | none |  |
| DS-PIPE-S4-001 | `2. V1_DESIGN.md` | `### Stage 4 — Claim Extraction & Dispute Localization` | `stage_rule` | design-level Stage 4 constraints | static + runtime | pending | none |  |
| DS-PIPE-S5-001 | `2. V1_DESIGN.md` | `### Stage 5 — Targeted Verification & Arbitration` | `stage_rule` | design-level Stage 5 constraints | static + runtime | pending | none |  |
| DS-PIPE-S6-001 | `2. V1_DESIGN.md` | `### Stage 6 — Synthesis & Report` | `output_contract` | design-level Stage 6 constraints | static + runtime | pending | none |  |
| DS-MODEL-ROLES-001 | `2. V1_DESIGN.md` | `## Model Roles` | `model_role_rule` | model family/version/role assignments | static + runtime | pending | none |  |
| DS-DISAGREEMENT-001 | `2. V1_DESIGN.md` | `## Disagreement Classification Framework` | `schema_contract` | dispute types and semantics | static + runtime | pending | none |  |
| DS-OUT-001 | `2. V1_DESIGN.md` | `## Output Contract` | `output_contract` | top-level output contract | static + render | pending | none |  |
| DS-OUT-TIERA-001 | `2. V1_DESIGN.md` | `### Tier A: Executive (what the user reads first)` | `output_contract` | executive content expectations | static + render | pending | none |  |
| DS-OUT-TIERB-001 | `2. V1_DESIGN.md` | `### Tier B: Analytical (what the user reads for understanding)` | `output_contract` | analytical content expectations | static + render | pending | none |  |
| DS-OUT-TIERC-001 | `2. V1_DESIGN.md` | `### Tier C: Evidentiary (what the user reads for verification)` | `output_contract` | evidentiary content expectations | static + render | pending | none |  |
| DS-OUT-TRACE-001 | `2. V1_DESIGN.md` | `### Trace File (separate from report)` | `output_contract` | trace output expectations | static + artifact | pending | none |  |
| DS-OUT-ANTIPATTERN-001 | `2. V1_DESIGN.md` | `### Output anti-patterns (must NOT contain)` | `anti_pattern_prohibition` | prohibited output behavior | static + render | pending | none |  |
| DS-SOURCESTRAT-001 | `2. V1_DESIGN.md` | `## Source Strategy (Locked)` | `cross_cutting_rule` | top-level source strategy | static + runtime | pending | none |  |
| DS-SOURCESTRAT-T1-001 | `2. V1_DESIGN.md` | `### Tier 1: Breadth Scouting (Stage 2)` | `stage_rule` | Stage 2 source strategy | static + runtime | pending | none |  |
| DS-SOURCESTRAT-T2-001 | `2. V1_DESIGN.md` | `### Tier 2: Dispute-Driven Targeting (Stage 5)` | `stage_rule` | Stage 5 source strategy | static + runtime | pending | none |  |
| DS-UNIT-ANALYSIS-001 | `2. V1_DESIGN.md` | `## Unit of Analysis (Locked)` | `schema_contract` | unit-of-analysis contract | static review | pending | none |  |
| DS-UNIT-DISAGREEMENT-001 | `2. V1_DESIGN.md` | `## Unit of Disagreement (Locked)` | `schema_contract` | unit-of-disagreement contract | static review | pending | none |  |
| DS-CCR-001 | `2. V1_DESIGN.md` | `## Cross-Cutting Requirements` | `cross_cutting_rule` | design-level cross-cutting rules | static + runtime | pending | none | split if needed |
| DS-LIMITATIONS-001 | `2. V1_DESIGN.md` | `## V1 Limitations & Accepted Tradeoffs` | `context_only` | accepted tradeoffs | static review | pending | none |  |
| DS-QUESTIONS-001 | `2. V1_DESIGN.md` | `## Remaining Design Questions` | `context_only` | explicit unresolved Tyler-side questions | static review | pending | none | may feed `tyler_ambiguity` rows |
| SC-CATEGORIES-001 | `3. V1_SCHEMAS.md` | `## Schema Categories` | `context_only` | schema organization overview | static review | pending | none |  |
| SC-SHAREDTYPES-001 | `3. V1_SCHEMAS.md` | `## Shared Types` | `schema_contract` | shared typed objects | static review | pending | none | split if needed |
| SC-ENUMS-001 | `3. V1_SCHEMAS.md` | `# --- Enums ---` | `enum/value_contract` | enum names and values | static + tests | pending | none | split by enum if needed |
| SC-COMMON-001 | `3. V1_SCHEMAS.md` | `## Common Objects` | `schema_contract` | common object fields | static + tests | pending | none | split if needed |
| SC-S1-001 | `3. V1_SCHEMAS.md` | `## Stage 1 — Intake & Decomposition` | `schema_contract` | Stage 1 schema | static + tests | pending | none |  |
| SC-S2-001 | `3. V1_SCHEMAS.md` | `## Stage 2 — Broad Retrieval & Evidence Normalization` | `schema_contract` | Stage 2 schema | static + tests | audited_gap_recorded | `AMB-S2-REASONING-001` | Stage 2 `Finding` schema omits `reasoning` even though the global prompt protocol implies it everywhere |
| SC-S3-001 | `3. V1_SCHEMAS.md` | `## Stage 3 — Independent Candidate Generation` | `schema_contract` | Stage 3 schema | static + tests | pending | none |  |
| SC-S4-001 | `3. V1_SCHEMAS.md` | `## Stage 4 — Claim Extraction & Dispute Localization` | `schema_contract` | Stage 4 schema | static + tests | pending | none |  |
| SC-S5-OUTPUT-001 | `3. V1_SCHEMAS.md` | `### Model output (one per investigated dispute):` | `schema_contract` | Stage 5 per-dispute output schema | static + tests | pending | none |  |
| SC-S5-FULL-001 | `3. V1_SCHEMAS.md` | `### Full stage output (orchestrator-assembled):` | `schema_contract` | Stage 5 full output schema | static + tests | pending | none |  |
| SC-S6-001 | `3. V1_SCHEMAS.md` | `## Stage 6 — Synthesis & Report` | `schema_contract` | Stage 6 schemas | static + tests | pending | none |  |
| SC-S6A-001 | `3. V1_SCHEMAS.md` | `### 6a. User-Steering Interrupt (conditional)` | `branch_or_skip_rule` | Stage 6a interrupt schema/contract | static + runtime | pending | none |  |
| SC-S6A-TRIGGER-001 | `3. V1_SCHEMAS.md` | `# --- Trigger logic (orchestrator code, not a schema) ---` | `branch_or_skip_rule` | Stage 6a trigger logic | static + runtime | pending | none |  |
| SC-S6B-001 | `3. V1_SCHEMAS.md` | `### 6b. Synthesis Report` | `schema_contract` | Stage 6b report schema | static + tests | pending | none |  |
| SC-PIPELINESTATE-001 | `3. V1_SCHEMAS.md` | `## Pipeline State` | `schema_contract` | pipeline state contract | static + tests | pending | none |  |
| SC-SKIPBRANCH-001 | `3. V1_SCHEMAS.md` | `## Skip and Branch Conditions` | `branch_or_skip_rule` | skip and branch logic | static + runtime | pending | none | split subunits below |
| SC-SKIP-S5-001 | `3. V1_SCHEMAS.md` | `### Stage 5 skip condition` | `branch_or_skip_rule` | Stage 5 skip logic | static + runtime | pending | none |  |
| SC-SKIP-S6INT-001 | `3. V1_SCHEMAS.md` | `### Stage 6 interrupt trigger` | `branch_or_skip_rule` | Stage 6 interrupt logic | static + runtime | pending | none |  |
| SC-MINMODEL-001 | `3. V1_SCHEMAS.md` | `### Minimum model threshold (Stage 3)` | `branch_or_skip_rule` | minimum successful model threshold | static + runtime | pending | none |  |
| SC-DECISIONCRIT-001 | `3. V1_SCHEMAS.md` | `## Decision-Criticality: v1 Operationalization` | `schema_contract` | decision criticality semantics | static + tests | pending | none |  |
| SC-IDSCHEME-001 | `3. V1_SCHEMAS.md` | `## ID Scheme` | `enum/value_contract` | identifier format rules | static + tests | pending | none |  |
| PR-GLOBAL-001 | `4. V1_PROMPTS.md` | `## Global Prompt Conventions [GPT]` | `prompt_template` | global prompt conventions | prompt render + static review | audited_gap_recorded | `AMB-S2-REASONING-001` | Shared output protocol over-claims reasoning-field applicability relative to Tyler's own Stage 2 `Finding` schema |
| PR-FRAMES-001 | `4. V1_PROMPTS.md` | `## Reasoning Frame Assignments` | `model_role_rule` | frame-to-model prompt assignment | static + runtime | audited_gap_recorded | `S3-FRAME-MODEL-001`, `AMB-S3-FRAME-001` | Prompt packet assignment is implemented locally, but the Build Plan disagrees and the packet carries an explicit discrepancy note |
| PR-INVENTORY-001 | `4. V1_PROMPTS.md` | `## Prompt Inventory` | `context_only` | prompt inventory completeness | static review | audited_context_only | none | inventory/index section only; normative prompt behavior is audited in specific prompt rows |
| PR-S1-SYSTEM-001 | `4. V1_PROMPTS.md` | `## Stage 1 — Intake & Decomposition / ### SYSTEM` | `prompt_template` | Stage 1 system prompt literalness | prompt render | pending | none |  |
| PR-S1-USER-001 | `4. V1_PROMPTS.md` | `## Stage 1 — Intake & Decomposition / ### USER` | `prompt_template` | Stage 1 user prompt literalness | prompt render | pending | none |  |
| PR-S1-CONSTRAINTS-001 | `4. V1_PROMPTS.md` | `## Stage 1 — Intake & Decomposition / ### Design constraints implemented:` | `context_only` | embedded prompt design notes | static review | pending | none | may generate subunits if normative |
| PR-S2-SYSTEM-001 | `4. V1_PROMPTS.md` | `## Stage 2 — Finding Extraction (per source) / ### SYSTEM` | `prompt_template` | Stage 2 finding extraction system prompt | prompt render | pending | none |  |
| PR-S2-USER-001 | `4. V1_PROMPTS.md` | `## Stage 2 — Finding Extraction (per source) / ### USER` | `prompt_template` | Stage 2 finding extraction user prompt | prompt render | pending | none |  |
| PR-S2-CONSTRAINTS-001 | `4. V1_PROMPTS.md` | `## Stage 2 — Finding Extraction (per source) / ### Design constraints implemented:` | `context_only` | embedded prompt design notes | static review | pending | none |  |
| PR-S2-QUERYTEMPLATE-001 | `4. V1_PROMPTS.md` | `## Stage 2 — Query Variant Generation (Orchestrator Template)` | `orchestrator_template` | Stage 2 query variant template | static + runtime | audited_gap_recorded | `S2-QUERY-MODEL-001`, `S2-QUERY-VARIANTS-001` | Prompt packet explicitly says this is orchestrator string expansion and defines a different variant family than the current live query-plan surface |
| PR-S3-BASE-001 | `4. V1_PROMPTS.md` | `## Stage 3 — Independent Candidate Generation / ### SYSTEM — Base (common to all three models)` | `prompt_template` | Stage 3 base system prompt | prompt render | pending | none |  |
| PR-S3-FRAMEA-001 | `4. V1_PROMPTS.md` | `## Stage 3 — Independent Candidate Generation / ### SYSTEM — Frame A: Step-Back Abstraction (assigned to GPT-5.4)` | `prompt_template` | Stage 3 Frame A prompt | prompt render | pending | none |  |
| PR-S3-FRAMEB-001 | `4. V1_PROMPTS.md` | `## Stage 3 — Independent Candidate Generation / ### SYSTEM — Frame B: Structured Decomposition (assigned to Gemini 3.1 Pro)` | `prompt_template` | Stage 3 Frame B prompt | prompt render | pending | none |  |
| PR-S3-FRAMEC-001 | `4. V1_PROMPTS.md` | `## Stage 3 — Independent Candidate Generation / ### SYSTEM — Frame C: Verification-First (assigned to Claude Opus 4.6)` | `prompt_template` | Stage 3 Frame C prompt | prompt render | pending | none |  |
| PR-S3-USER-001 | `4. V1_PROMPTS.md` | `## Stage 3 — Independent Candidate Generation / ### USER (common to all three models)` | `prompt_template` | Stage 3 shared user prompt | prompt render | pending | none |  |
| PR-S3-EVIDENCE-001 | `4. V1_PROMPTS.md` | `## Stage 3 — Independent Candidate Generation / ### Evidence for [{{sqe.sub_question_id}}]` | `prompt_template` | Stage 3 evidence block formatting | prompt render | pending | none |  |
| PR-S3-CONSTRAINTS-001 | `4. V1_PROMPTS.md` | `## Stage 3 — Independent Candidate Generation / ### Design constraints implemented:` | `context_only` | embedded prompt design notes | static review | pending | none |  |
| PR-S4-SYSTEM-001 | `4. V1_PROMPTS.md` | `## Stage 4 — Claim Extraction & Dispute Localization / ### SYSTEM` | `prompt_template` | Stage 4 system prompt | prompt render | pending | none |  |
| PR-S4-USER-001 | `4. V1_PROMPTS.md` | `## Stage 4 — Claim Extraction & Dispute Localization / ### USER` | `prompt_template` | Stage 4 user prompt | prompt render | pending | none |  |
| PR-S4-CONSTRAINTS-001 | `4. V1_PROMPTS.md` | `## Stage 4 — Claim Extraction & Dispute Localization / ### Design constraints implemented:` | `context_only` | embedded prompt design notes | static review | pending | none |  |
| PR-S5-COUNTERFACTUAL-001 | `4. V1_PROMPTS.md` | `## Stage 5 — Targeted Verification & Arbitration / ### Counterfactual Query Generation (Orchestrator Template)` | `orchestrator_template` | Stage 5 query generation template | static + runtime | pending | none |  |
| PR-S5-SYSTEM-001 | `4. V1_PROMPTS.md` | `## Stage 5 — Targeted Verification & Arbitration / ### SYSTEM` | `prompt_template` | Stage 5 system prompt | prompt render | pending | none |  |
| PR-S5-USER-001 | `4. V1_PROMPTS.md` | `## Stage 5 — Targeted Verification & Arbitration / ### USER` | `prompt_template` | Stage 5 user prompt | prompt render | pending | none |  |
| PR-S5-CONSTRAINTS-001 | `4. V1_PROMPTS.md` | `## Stage 5 — Targeted Verification & Arbitration / ### Design constraints implemented:` | `context_only` | embedded prompt design notes | static review | pending | none |  |
| PR-S6-COMPACTION-001 | `4. V1_PROMPTS.md` | `## Stage 6b — Synthesis & Report / ### Context Compaction (Orchestrator Logic)` | `orchestrator_template` | Stage 6 compaction logic | static + runtime | pending | none |  |
| PR-S6-SYSTEM-001 | `4. V1_PROMPTS.md` | `## Stage 6b — Synthesis & Report / ### SYSTEM` | `prompt_template` | Stage 6 system prompt | prompt render | pending | none |  |
| PR-S6-USER-001 | `4. V1_PROMPTS.md` | `## Stage 6b — Synthesis & Report / ### USER` | `prompt_template` | Stage 6 user prompt | prompt render | pending | none |  |
| PR-S6-CONSTRAINTS-001 | `4. V1_PROMPTS.md` | `## Stage 6b — Synthesis & Report / ### Design constraints implemented:` | `context_only` | embedded prompt design notes | static review | pending | none |  |
| PR-NOTES-PSI-001 | `4. V1_PROMPTS.md` | `## Notes for Developer / ### Prompt-Schema Interaction` | `cross_cutting_rule` | prompt/schema interaction rules | static review | pending | none |  |
| PR-NOTES-SHAREDOUTPUT-001 | `4. V1_PROMPTS.md` | `## Notes for Developer / ### Shared Output Protocol` | `cross_cutting_rule` | shared output protocol | static review | audited_gap_recorded | `AMB-S2-REASONING-001` | Shared output guidance conflicts with Tyler's Stage 2 `Finding` schema and must be interpreted selectively in the local prompt surface |
| PR-NOTES-TEMPLATEVARS-001 | `4. V1_PROMPTS.md` | `## Notes for Developer / ### Template Variable Resolution` | `cross_cutting_rule` | template variable semantics | static review | pending | none |  |
| PR-NOTES-ORCHFIELDS-001 | `4. V1_PROMPTS.md` | `## Notes for Developer / ### Orchestrator-Computed Fields (Tier 2 Enforcement)` | `cross_cutting_rule` | orchestrator-computed field rules | static + runtime | pending | none |  |
| PR-NOTES-ORCHVARS-001 | `4. V1_PROMPTS.md` | `## Notes for Developer / ### Orchestrator-Constructed Variables` | `cross_cutting_rule` | orchestrator variable construction | static review | pending | none |  |
| PR-NOTES-DATASTRUCT-001 | `4. V1_PROMPTS.md` | `## Notes for Developer / ### Data Structure Conventions` | `schema_contract` | data structure conventions | static review | pending | none |  |
| PR-NOTES-CONTEXTCOMP-001 | `4. V1_PROMPTS.md` | `## Notes for Developer / ### Context Compaction Implementation` | `cross_cutting_rule` | compaction implementation rules | static + runtime | pending | none |  |
| PR-NOTES-TOKENBUDGET-001 | `4. V1_PROMPTS.md` | `## Notes for Developer / ### Token Budget Estimates (rough, for planning)` | `context_only` | planning-only token notes | static review | pending | none |  |
| PR-NOTES-NOVELTY-001 | `4. V1_PROMPTS.md` | `## Notes for Developer / ### Novelty/Delta Detection — V1 Simplification (Design Constraint #6)` | `cross_cutting_rule` | novelty/delta detection rule | static + runtime | pending | none |  |
