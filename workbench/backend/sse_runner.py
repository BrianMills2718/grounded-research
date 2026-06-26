"""SSE-instrumented grounded-research pipeline runner.

Wraps the adjudication pipeline phases with ui_protocol SSE events so the
workbench frontend can show live phase progress.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from ui_protocol import (
    DoneEvent,
    ErrorEvent,
    SSEEmitter,
    StatusEvent,
    ToolEndEvent,
    ToolStartEvent,
)


async def run_pipeline_with_sse(
    question: str,
    output_dir: Path,
    config_profile: str,
    emitter: SSEEmitter,
) -> None:
    """Run the grounded-research pipeline and emit SSE events at each phase boundary."""
    import os

    if config_profile:
        os.environ["GROUNDED_RESEARCH_CONFIG"] = config_profile

    run_id = uuid.uuid4().hex[:12]
    trace_id = f"workbench/{run_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    seq = emitter.next_seq

    try:
        from grounded_research.config import get_depth_config
        depth = get_depth_config()

        # ── Phase 1: Decompose ──────────────────────────────────────────────
        t0 = datetime.now(timezone.utc)
        await emitter.emit(ToolStartEvent(
            tool="decompose_question",
            tool_reasoning="Decompose the research question into typed sub-questions",
            args={"question": question[:200]},
            seq=seq(),
        ))
        from grounded_research.decompose import decompose_question_tyler_v1
        stage1 = await decompose_question_tyler_v1(question, f"{trace_id}/stage1")
        latency = (datetime.now(timezone.utc) - t0).total_seconds()
        sub_q_preview = "\n".join(
            f"  [{sq.type}] {sq.question[:80]}"
            for sq in stage1.sub_questions[:5]
        )
        await emitter.emit(ToolEndEvent(
            tool="decompose_question",
            result_preview=f"Core: {stage1.core_question[:120]}\n\nSub-questions:\n{sub_q_preview}",
            has_error=False,
            error="",
            latency_s=latency,
            seq=seq(),
        ))

        # ── Phase 2: Collect evidence ──────────────────────────────────────
        t0 = datetime.now(timezone.utc)
        await emitter.emit(ToolStartEvent(
            tool="collect_evidence",
            tool_reasoning="Collect web evidence driven by sub-questions",
            args={
                "sub_questions": len(stage1.sub_questions),
                "num_queries": depth["num_queries"],
                "max_sources": depth["max_sources"],
            },
            seq=seq(),
        ))
        from grounded_research.collect import collect_evidence_tyler_v1
        stage2, bundle = await collect_evidence_tyler_v1(
            stage1,
            f"{trace_id}/stage2",
            num_queries=depth["num_queries"],
            max_sources=depth["max_sources"],
        )
        latency = (datetime.now(timezone.utc) - t0).total_seconds()
        bundle_path = output_dir / "collected_bundle.json"
        bundle_path.write_text(bundle.model_dump_json(indent=2))
        stage1_path = output_dir / "tyler_stage_1.json"
        stage1_path.write_text(stage1.model_dump_json(indent=2))
        stage2_path = output_dir / "tyler_stage_2.json"
        stage2_path.write_text(stage2.model_dump_json(indent=2))
        await emitter.emit(ToolEndEvent(
            tool="collect_evidence",
            result_preview=f"{len(bundle.sources)} sources, {len(bundle.evidence)} evidence items, {len(bundle.gaps)} gaps",
            has_error=False,
            error="",
            latency_s=latency,
            seq=seq(),
        ))

        # ── Phases 3-6 via run_pipeline ───────────────────────────────────
        await emitter.emit(StatusEvent(
            message="Handing off to adjudication pipeline (analyze → canonicalize → adjudicate → export)…",
            seq=seq(),
        ))

        # Pre-emit tool_start for each remaining phase — they'll resolve after run_pipeline
        remaining_phases = ["analyze", "canonicalize", "adjudicate", "export"]
        phase_start_times: dict[str, datetime] = {}
        for phase in remaining_phases:
            phase_start_times[phase] = datetime.now(timezone.utc)
            await emitter.emit(ToolStartEvent(
                tool=phase,
                tool_reasoning=f"Run {phase} phase of the adjudication pipeline",
                args={},
                seq=seq(),
            ))

        from engine import run_pipeline
        from grounded_research.runtime_policy import configure_run_runtime
        configure_run_runtime(run_id, output_dir)

        state = await run_pipeline(
            bundle_path,
            output_dir,
            tyler_stage_1_result=stage1,
            tyler_stage_2_result=stage2,
        )

        # Emit tool_end for each phase using phase_traces from state
        for phase in remaining_phases:
            trace = next((t for t in state.phase_traces if t.phase == phase), None)
            if trace:
                latency = (trace.completed_at - trace.started_at).total_seconds()
                await emitter.emit(ToolEndEvent(
                    tool=phase,
                    result_preview=trace.output_summary or f"{phase} complete",
                    has_error=not trace.succeeded,
                    error="" if trace.succeeded else f"{phase} failed",
                    latency_s=latency,
                    seq=seq(),
                ))
            else:
                # Phase didn't run (pipeline may have failed early)
                await emitter.emit(ToolEndEvent(
                    tool=phase,
                    result_preview="phase did not run",
                    has_error=True,
                    error="no trace recorded",
                    latency_s=0.0,
                    seq=seq(),
                ))

        # Build answer from synthesis report
        answer = "(no synthesis report)"
        if state.tyler_stage_6_result is not None:
            answer = state.tyler_stage_6_result.executive_recommendation[:400]
        elif not state.success:
            warnings = [w.message for w in state.warnings[:3]]
            answer = "Pipeline failed: " + "; ".join(warnings)

        total_elapsed = sum(
            (t.completed_at - t.started_at).total_seconds()
            for t in state.phase_traces
        )
        await emitter.emit(DoneEvent(
            answer=answer,
            finish_reason="stop" if state.success else "error",
            num_turns=len(state.phase_traces) + 2,
            n_tool_calls=len(state.phase_traces) + 2,
            elapsed_s=total_elapsed,
            tool_details=[],
            conversation_trace=[],
            seq=seq(),
        ))

    except Exception as exc:
        await emitter.emit(ErrorEvent(
            message=str(exc),
            detail=type(exc).__name__,
        ))
    finally:
        await emitter.close()
