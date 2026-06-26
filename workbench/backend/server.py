"""Grounded Research workbench FastAPI server.

Start with:
    cd ~/projects/grounded-research/workbench/backend
    uvicorn server:app --host 0.0.0.0 --port 5201 --reload

Frontend dev server (Vite) runs on :5202 and proxies /api → :5201.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ui_protocol import SSEEmitter
from sse_runner import run_pipeline_with_sse  # absolute import; run via: uvicorn server:app from workbench/backend/

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

app = FastAPI(title="Grounded Research Workbench")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job registry — resets on server restart
_jobs: dict[str, SSEEmitter] = {}


class RunRequest(BaseModel):
    question: str
    config: str = "standard"  # "testing" | "standard"


@app.post("/api/run")
async def start_run(body: RunRequest) -> dict:
    """Start a pipeline run. Returns job_id for SSE stream."""
    job_id = uuid.uuid4().hex[:12]
    emitter = SSEEmitter()
    _jobs[job_id] = emitter

    slug = body.question[:40].lower().replace(" ", "_").replace("?", "").replace("/", "_")
    output_dir = PROJECT_ROOT / "output" / f"workbench_{job_id}_{slug}"

    asyncio.create_task(run_pipeline_with_sse(
        question=body.question,
        output_dir=output_dir,
        config_profile=body.config,
        emitter=emitter,
    ))
    return {"job_id": job_id}


@app.get("/api/stream/{job_id}")
async def stream_run(job_id: str) -> StreamingResponse:
    """SSE stream for a running job."""
    emitter = _jobs.get(job_id)
    if emitter is None:
        raise HTTPException(404, detail=f"Unknown job_id: {job_id}")
    return StreamingResponse(emitter.stream(), media_type="text/event-stream")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "active_jobs": len(_jobs)}
