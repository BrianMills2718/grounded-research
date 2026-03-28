# grounded-research

Multi-analyst research platform that beats cached Perplexity Deep Research on the tracked 6-question benchmark set in the shipped calibrated path, and whose Tyler-native path now also beats cached Perplexity on the tracked UBI case. It supports both raw-question runs and pre-built evidence bundles, then decomposes questions, runs 3 independent LLM analysts with different reasoning lenses, detects disagreements, resolves factual conflicts with fresh evidence, and produces grounded reports with full provenance.

## Results

Blind evaluation (GPT-5-nano judge, citation format ignored):

| Question | grounded-research | Perplexity Deep | Winner |
|----------|:-:|:-:|:-:|
| EU sanctions effectiveness | **23**/25 | 22/25 | Pipeline |
| PFAS health risks | **24**/25 | 20/25 | Pipeline |
| Intermittent fasting | **24**/25 | 22/25 | Pipeline |
| LLM capabilities | **24**/25 | 20/25 | Pipeline |
| Universal basic income | **24**/25 | 23/25 | Pipeline |
| Gut microbiome & mental health | **20**/25 | 18/25 | Pipeline |

Cost: ~$0.06/run (standard), ~$0.25 (deep), ~$1.00 (thorough).

## How it works

```
Question
  → Decompose into typed sub-questions (factual, causal, comparative, evaluative)
  → Generate search queries per sub-question (parallel)
  → Fetch 50-150 sources with quality scoring (parallel)
  → 3 independent analysts × 3 reasoning frames (parallel)
  → Extract claims, deduplicate, detect disputes
  → Arbitrate decision-critical disputes with fresh evidence
  → Synthesize report (analytical or grounded mode)
```

Every claim traces back through: report → claim ledger → analyst → evidence → source URL.

## Usage

```bash
# Standard depth (~$0.06, 50 sources, 3 min)
python engine.py "Your research question"

# Deep research (~$0.25, 100 sources, 10 min)
python engine.py "Your question" --depth deep

# Thorough research (~$1.00, 150 sources, 20 min)
python engine.py "Your question" --depth thorough

# From a pre-built evidence bundle
python engine.py --fixture path/to/bundle.json

# Custom output directory
python engine.py "Your question" --output-dir output/my_run
```

## Output

Each run produces:
- `report.md` — long-form research report (5K-15K words depending on depth)
- `summary.md` — structured summary with cited claims
- `trace.json` — full pipeline state with provenance
- `handoff.json` — structured artifact for downstream systems
- `decomposition.json` — sub-questions, optimization axes, research plan
- `collected_bundle.json` — raw evidence bundle (reusable)

## Key features

- **Question decomposition** with typed sub-questions, falsification targets, and validation with retry
- **Distinct analyst roles**: currently configured to the closest available Tyler role mapping
  (`gpt-5.4-mini`, `gemini-2.5-flash`, `gpt-5.4-nano`) with three reasoning frames
- **3 reasoning frames**: verification-first, structured decomposition, step-back abstraction
- **LLM source quality scoring**: authoritative / reliable / unknown / unreliable
- **Dispute detection** with severity classification and deterministic routing
- **Fresh evidence arbitration** for decision-critical factual conflicts
- **Configurable synthesis**: analytical mode (inferences beyond sources, marked) or grounded mode (ledger-only)
- **Model fallback chains** on all LLM calls
- **User steering** for preference/ambiguity disputes (interactive TTY)
- **Full provenance** always available in trace.json regardless of report mode

## Configuration

All operational policy in `config/config.yaml`:
- Model assignments and fallback chains
- Depth profiles (standard / deep / thorough)
- Analyst models and reasoning frames
- Budget limits
- Synthesis mode (analytical / grounded)
- Evidence policy (compression threshold, recency)

## Architecture

- 20 YAML prompt templates in `prompts/`
- All LLM calls via [llm_client](https://github.com/BrianMills2718/llm_client)
- Web search via [open_web_retrieval](https://github.com/BrianMills2718/open_web_retrieval)
- 23 test modules covering phase-boundary contracts and Tyler-native runtime slices
- 7 ADRs documenting architectural decisions

## Setup

Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e path/to/llm_client
pip install -e path/to/open_web_retrieval
```

Requires API keys for: Gemini, OpenRouter (routes to current configured OpenAI/Gemini models), Brave Search. Optionally: Perplexity (for comparison scripts).

## Documentation

- `docs/ROADMAP.md` — priorities and next steps
- `docs/COMPETITIVE_ANALYSIS.md` — full SOTA comparison with Perplexity, GPT-Researcher
- `docs/JUDGE_CRITIQUES.md` — where the pipeline loses points and why
- `docs/FEATURE_STATUS.md` — 47/52 scorecard features implemented
- `docs/TECH_DEBT.md` — known issues for future work
- `docs/adr/` — architectural decision records
- `v1_Pruning_Scorecard.xlsx` — original feature scorecard with implementation status
