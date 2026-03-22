#!/usr/bin/env python3
"""Run the repo's core governance checks from one stable entrypoint.

This target keeps the most important documentation and plan gates behind a
single command so CI can fail fast when governance drifts:

- doc coupling rules
- plan-status synchronization
- machine-readable ADR invariants for Phase 4
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class CheckCommand:
    """One concrete command that should succeed for the aggregate target to pass."""

    label: str
    argv: list[str]


def _run_check(command: CheckCommand) -> None:
    """Run one check in the repo root and stop immediately on failure."""
    print(f"[ci-checks] {command.label}", flush=True)
    result = subprocess.run(command.argv, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    """Run the repository governance checks in a fixed order."""
    checks = [
        CheckCommand(
            label="doc coupling",
            argv=[sys.executable, "scripts/check_doc_coupling.py", "--strict"],
        ),
        CheckCommand(
            label="plan status",
            argv=[sys.executable, "scripts/sync_plan_status.py", "--check"],
        ),
        CheckCommand(
            label="ADR-0004 invariants",
            argv=[
                sys.executable,
                "scripts/check_adr_invariants.py",
                "--adr",
                "docs/adr/0004-agentic-verification-and-fail-loud-phase4.md",
                "--strict",
            ],
        ),
    ]

    for check in checks:
        _run_check(check)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
