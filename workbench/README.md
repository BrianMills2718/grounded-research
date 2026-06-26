# Grounded Research Workbench

Live agent runner UI for the adjudication pipeline.

## Start

```bash
# Terminal 1 — backend (FastAPI + SSE)
cd ~/projects/grounded-research
pip install -e . && pip install -e ~/projects/shared_ui/python
pip install fastapi uvicorn
uvicorn workbench.backend.server:app --host 0.0.0.0 --port 5201 --reload

# Terminal 2 — frontend (Vite)
cd ~/projects/grounded-research/workbench/frontend
npm install
npm run dev
# → http://localhost:5202
```

## Phases shown in the runner

| Phase | What it does |
|-------|-------------|
| `decompose_question` | LLM splits the question into typed sub-questions |
| `collect_evidence` | Web search driven by sub-questions |
| `analyze` | 3 independent analyst passes |
| `canonicalize` | Claim deduplication and ledger |
| `adjudicate` | Dispute classification and resolution |
| `export` | Synthesis report + downstream handoff |

Use "testing" config profile for cheap models during development.
