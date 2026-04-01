"""Runtime policy helpers for pipeline execution.

This module owns project-local operational policy applied before
the first `llm_client` call in a run:

- run-local observability DB path selection
- timeout policy: ban request-level timeouts (observe, don't kill)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from grounded_research.config import get_runtime_reliability_config


def configure_run_runtime(run_id: str, output_dir: Path) -> dict[str, Any]:
    """Configure process-level runtime policy for one pipeline run.

    The policy is intentionally applied at the project layer so benchmark runs
    do not contend on a shared observability database.

    Request-level timeouts are disabled (LLM_CLIENT_TIMEOUT_POLICY=ban).
    The llm_client safety timeout (300s dead-connection detector) still applies.
    See docs/plans/llm_call_observability.md for rationale.
    """
    cfg = get_runtime_reliability_config()
    output_dir.mkdir(parents=True, exist_ok=True)

    db_path: Path | None = None
    if bool(cfg.get("use_run_local_observability_db", True)):
        db_path = output_dir / "llm_observability.db"
        os.environ["LLM_CLIENT_DB_PATH"] = str(db_path)

    # Ban request-level timeouts — observe hangs, don't kill calls.
    # Safety timeout (dead-connection detector, 300s) still applies via llm_client.
    os.environ["LLM_CLIENT_TIMEOUT_POLICY"] = "ban"

    if "llm_client" in sys.modules:
        from llm_client import configure_logging

        configure_logging(db_path=db_path)

    return {
        "run_id": run_id,
        "db_path": str(db_path) if db_path is not None else None,
        "timeout_policy": "ban",
    }
