"""Runtime policy helpers for long benchmark-safe pipeline execution.

This module owns project-local operational policy that must be applied before
the first `llm_client` call in a run:

- run-local observability DB path selection
- timeout policy selection
- typed request-timeout lookup by task
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
    do not contend on a shared observability database and so long structured
    calls use an explicit timeout policy.
    """
    cfg = get_runtime_reliability_config()
    output_dir.mkdir(parents=True, exist_ok=True)

    db_path: Path | None = None
    if bool(cfg.get("use_run_local_observability_db", True)):
        db_path = output_dir / "llm_observability.db"
        os.environ["LLM_CLIENT_DB_PATH"] = str(db_path)

    timeout_policy = str(cfg.get("timeout_policy", "allow"))
    os.environ["LLM_CLIENT_TIMEOUT_POLICY"] = timeout_policy

    if "llm_client" in sys.modules:
        from llm_client import configure_logging

        configure_logging(db_path=db_path)

    return {
        "run_id": run_id,
        "db_path": str(db_path) if db_path is not None else None,
        "timeout_policy": timeout_policy,
    }


def get_request_timeout(task_name: str) -> int:
    """Return the configured request timeout in seconds for one task surface."""
    cfg = get_runtime_reliability_config()
    request_timeouts = cfg.get("request_timeouts_s", {})
    if not isinstance(request_timeouts, dict):
        raise TypeError("runtime_reliability.request_timeouts_s must be a mapping")
    raw_timeout = request_timeouts.get(task_name)
    if raw_timeout is None:
        raise KeyError(f"No runtime timeout configured for task '{task_name}'")
    timeout = int(raw_timeout)
    if timeout < 1:
        raise ValueError(f"Runtime timeout for task '{task_name}' must be >= 1")
    return timeout
