# Grounded Research Artifact Register

Wiki home: http://localhost:8088/index.php/Project_Wiki

## Primary Reviewer Artifacts

| Artifact | Role | Portfolio meaning |
|---|---|---|
| [PROJECT.md](../PROJECT.md) | Dossier entrypoint | Frames the repo as adjudication-centered research architecture. |
| [README.md](../README.md) | System overview and benchmark summary | Gives the top-level capability and comparison claims. |
| [docs/MAINTAINER_START_HERE.md](MAINTAINER_START_HERE.md) | Maintainer entrypoint | Defines the Tyler authority chain, local gates, stop lines, and MCP extension boundary. |
| [docs/ADJUDICATION_WALKTHROUGH.md](ADJUDICATION_WALKTHROUGH.md) | Portfolio walkthrough | Explains the question -> analysts -> claim ledger -> disputes -> report path. |
| [docs/METHODOLOGY.md](METHODOLOGY.md) | Methodology spine | Summarizes the adjudication method and failure modes. |
| [docs/VALIDATION.md](VALIDATION.md) | Validation register | Separates tracked evidence from broader claims. |
| [docs/CONCERNS.md](CONCERNS.md) | Concern register | Lists remaining portfolio and evidence risks. |

## Architecture And Contract Artifacts

| Artifact | Role | Notes |
|---|---|---|
| [docs/ARCHITECTURE_ONE_PAGE.md](ARCHITECTURE_ONE_PAGE.md) | Architecture summary | Defines ownership boundaries and runtime layers. |
| [docs/CONTRACTS.md](CONTRACTS.md) | Stage contracts | Defines phase inputs, outputs, success, and failure semantics. |
| [docs/DOMAIN_MODEL.md](DOMAIN_MODEL.md) | Domain model | Defines research questions, evidence, claims, analysts, disputes, and reports. |
| [docs/FEATURE_STATUS.md](FEATURE_STATUS.md) | Feature scorecard | Maps original scorecard features to implementation status. |
| [docs/ROADMAP.md](ROADMAP.md) | Roadmap | Current state and next expansion gates. |
| [docs/wiki/](wiki/) | Concept wiki | Durable Tyler compliance and extension-boundary notes for maintainers. |

## Audit And Evaluation Artifacts

| Artifact | Evidence area | Notes |
|---|---|---|
| [docs/TYLER_SPEC_GAP_LEDGER.md](TYLER_SPEC_GAP_LEDGER.md) | Code-vs-spec ledger | Canonical truth surface for Tyler packet compliance. |
| [docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md](TYLER_FULL_SPEC_AUDIT_MATRIX.md) | Audit coverage | Exhaustive Tyler packet review matrix. |
| [docs/TYLER_TRACEABILITY.md](TYLER_TRACEABILITY.md) | Traceability system | Explains the machine-checkable Tyler requirement-to-code/test report. |
| [docs/TYLER_FROZEN_EVAL_STATUS.md](TYLER_FROZEN_EVAL_STATUS.md) | Frozen eval status | Tracks frozen evaluation gates. |
| [docs/COMPETITIVE_ANALYSIS.md](COMPETITIVE_ANALYSIS.md) | Baseline comparison | Comparison framing against other research systems. |
| [docs/JUDGE_CRITIQUES.md](JUDGE_CRITIQUES.md) | Judge feedback | Where the pipeline loses points and why. |

## Runtime Artifacts

| Artifact | Role | Notes |
|---|---|---|
| `engine.py` | CLI/runtime entrypoint | Runs raw-question and fixture-backed flows. |
| [src/grounded_research/models.py](../src/grounded_research/models.py) | Runtime models | Project-local pipeline state and artifacts. |
| [src/grounded_research/tyler_v1_models.py](../src/grounded_research/tyler_v1_models.py) | Tyler models | Tyler-native schema layer. |
| [prompts/](../prompts) | Prompt templates | YAML/Jinja2 prompt data for Tyler stages. |
| [config/config.yaml](../config/config.yaml) | Operational policy | Model assignments, depth profiles, budgets, and synthesis policy. |

## Missing Portfolio Artifacts

- A compact public source-to-claim walkthrough.
- A saved non-sensitive run bundle with `report.md`, `summary.md`,
  `trace.json`, and handoff artifact.
- A short benchmark note that scopes the Perplexity/Tyler comparison claims.
- A wiki-rendered trace excerpt showing how a final claim resolves to evidence.

## Historical Tyler Artifacts

These files are preserved in `docs/archive/` because later ledger/status
documents supersede their current-state claims:

- `docs/archive/TYLER_FINAL_COMPLIANCE_AUDIT.md`
- `docs/archive/TYLER_V1_DELIVERY_SUMMARY.md`
- `docs/archive/TYLER_LITERAL_PARITY_AUDIT.md`
- `docs/archive/TYLER_LITERAL_PROMPT_FIDELITY_AUDIT.md`
- `docs/archive/TYLER_PROMPT_LITERALNESS_MATRIX.md`
- `docs/archive/TYLER_FEEDBACK_RESPONSE.md`
