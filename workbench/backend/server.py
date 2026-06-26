"""Grounded Research workbench FastAPI server.

Start with:
    cd ~/projects/grounded-research/workbench/backend
    uvicorn server:app --host 0.0.0.0 --port 5201 --reload

Frontend dev server (Vite) runs on :5202 and proxies /api → :5201.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ui_protocol import SSEEmitter
from sse_runner import run_pipeline_with_sse  # absolute import; run via: uvicorn server:app from workbench/backend/

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

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


class RunMeta(BaseModel):
    id: str = Field(description="Hex job ID parsed from directory name")
    dir: str = Field(description="Output directory name")
    question: str = Field(description="Research question derived from directory slug")
    has_report: bool = Field(description="Whether report.md exists")
    has_summary: bool = Field(description="Whether summary.md exists")
    mtime: float = Field(description="Directory modification time (Unix timestamp)")


class ReportResponse(BaseModel):
    run_id: str
    content: str = Field(description="Markdown content of report.md")


class SummaryResponse(BaseModel):
    run_id: str
    content: str = Field(description="Markdown content of summary.md")


class TraceResponse(BaseModel):
    run_id: str
    file: str = Field(description="Filename: handoff.json or trace.json")
    data: dict = Field(description="Parsed JSON content of the trace file")


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


@app.get("/api/runs")
async def list_runs() -> list[RunMeta]:
    """List completed pipeline runs (have report.md)."""
    runs = []
    if not OUTPUT_DIR.exists():
        return runs
    for d in sorted(OUTPUT_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not d.is_dir():
            continue
        report = d / "report.md"
        summary = d / "summary.md"
        # Parse job_id and question from dirname: workbench_{job_id}_{slug}
        m = re.match(r"workbench_([a-f0-9]+)_(.+)", d.name)
        if not m:
            continue
        job_id, slug = m.group(1), m.group(2)
        question = slug.replace("_", " ").strip()
        runs.append(RunMeta(
            id=job_id,
            dir=d.name,
            question=question,
            has_report=report.exists(),
            has_summary=summary.exists(),
            mtime=d.stat().st_mtime,
        ))
    return runs


@app.get("/api/runs/{run_id}/report")
async def get_report(run_id: str) -> ReportResponse:
    """Return report.md content for a completed run."""
    if not OUTPUT_DIR.exists():
        raise HTTPException(404, "No output directory")
    for d in OUTPUT_DIR.iterdir():
        if d.is_dir() and d.name.startswith(f"workbench_{run_id}_"):
            report = d / "report.md"
            if report.exists():
                return ReportResponse(run_id=run_id, content=report.read_text())
            raise HTTPException(404, f"No report.md in {d.name}")
    raise HTTPException(404, f"No run found with id: {run_id}")


@app.get("/api/runs/{run_id}/trace")
async def get_trace(run_id: str) -> TraceResponse:
    """Return trace.json or handoff.json for a completed run."""
    import json as _json
    if not OUTPUT_DIR.exists():
        raise HTTPException(404, "No output directory")
    for d in OUTPUT_DIR.iterdir():
        if d.is_dir() and d.name.startswith(f"workbench_{run_id}_"):
            # prefer handoff.json (richer), fall back to trace.json
            for fname in ("handoff.json", "trace.json"):
                f = d / fname
                if f.exists():
                    return TraceResponse(run_id=run_id, file=fname, data=_json.loads(f.read_text()))
            raise HTTPException(404, f"No trace data in {d.name}")
    raise HTTPException(404, f"No run found with id: {run_id}")


@app.get("/api/runs/{run_id}/summary")
async def get_summary(run_id: str) -> SummaryResponse:
    """Return summary.md content for a completed run."""
    if not OUTPUT_DIR.exists():
        raise HTTPException(404, "No output directory")
    for d in OUTPUT_DIR.iterdir():
        if d.is_dir() and d.name.startswith(f"workbench_{run_id}_"):
            summary = d / "summary.md"
            if summary.exists():
                return SummaryResponse(run_id=run_id, content=summary.read_text())
            raise HTTPException(404, f"No summary.md in {d.name}")
    raise HTTPException(404, f"No run found with id: {run_id}")
