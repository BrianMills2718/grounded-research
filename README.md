# grounded-research

Adjudication-first research platform. Runs independent LLM analysts over shared evidence, builds a claim ledger with disputes, and resolves factual conflicts with fresh evidence.

## What it does

1. **Ingest** evidence from upstream systems (research_v3, manual bundles, web search)
2. **Analyze** with 3 independent analysts (different model families, different reasoning frames)
3. **Canonicalize** into claims, deduplicate, detect disputes
4. **Adjudicate** decision-critical disputes with fresh evidence
5. **Export** grounded report with full provenance trace

The canonical artifact is the **claim ledger**, not the prose report. The report renders structured state.

## Usage

```bash
# From a question (collects evidence automatically)
python engine.py "What sanctions has the EU imposed on Russia?"

# From a pre-built evidence bundle
python engine.py --fixture path/to/bundle.json

# With custom output directory
python engine.py "Your question" --output-dir output/my_run
```

## Output

Each run produces:
- `report.md` — long-form research report (3,000-6,000 words)
- `summary.md` — structured summary with cited claims
- `trace.json` — full pipeline state with provenance
- `handoff.json` — downstream artifact for onto-canon

## Architecture

- 3 cross-family analysts: Gemini 2.5 Flash, GPT-5-nano, DeepSeek Chat
- 3 reasoning frames: verification-first, structured decomposition, step-back abstraction
- Prompts as YAML/Jinja2 templates (`prompts/`)
- All LLM calls via [llm_client](https://github.com/BrianMills2718/llm_client)
- Web search via [open_web_retrieval](https://github.com/BrianMills2718/open_web_retrieval)

## Validation

Pipeline beats single-shot synthesis on factual questions with evidence conflicts (GPT-5-nano judge, 3/4 wins). Value comes from multi-analyst structural framing and fresh-evidence arbitration.

See `docs/PLAN.md` for full comparison results and `docs/adr/` for architectural decisions.

## Requirements

Python 3.11+. Dependencies: pydantic, pyyaml, jinja2, plus `llm_client` and `open_web_retrieval` installed in the venv.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e ~/projects/llm_client
pip install -e ~/projects/open_web_retrieval
```
