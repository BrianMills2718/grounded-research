"""Preflight local-only dependencies required by the maintainer test gate.

The repo intentionally keeps large runtime outputs out of git, but several
tests verify checked-in manifests against those frozen artifacts. This script
fails early with actionable setup guidance when a worktree lacks the local
shared packages or ignored output directories needed by `make check`.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIR = REPO_ROOT / "config" / "eval_manifests"


@dataclass(frozen=True)
class Finding:
    """One local environment prerequisite failure."""

    check: str
    message: str
    remediation: str


def _manifest_artifact_paths() -> list[Path]:
    """Return all artifact paths referenced by checked-in eval manifests."""

    artifact_paths: list[Path] = []
    for manifest_path in sorted(MANIFEST_DIR.glob("*.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for variant in manifest.get("variants", []):
            for artifact in variant.get("files", {}).values():
                raw_path = artifact.get("path")
                if raw_path:
                    artifact_paths.append(REPO_ROOT / raw_path)
    return sorted(set(artifact_paths))


def check_environment() -> dict[str, Any]:
    """Check local prerequisites needed by the full maintainer gate."""

    findings: list[Finding] = []

    if importlib.util.find_spec("epistemic_contracts") is None:
        findings.append(
            Finding(
                check="epistemic_contracts_import",
                message="Python cannot import the local epistemic_contracts package.",
                remediation=(
                    "Install the sibling shared package into the active venv: "
                    "python -m pip install -e ../epistemic-contracts"
                ),
            )
        )

    missing_artifacts = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in _manifest_artifact_paths()
        if not path.exists()
    ]
    if missing_artifacts:
        findings.append(
            Finding(
                check="frozen_eval_artifacts",
                message=(
                    f"{len(missing_artifacts)} frozen eval artifact(s) referenced by "
                    "config/eval_manifests are missing from this worktree."
                ),
                remediation=(
                    "Restore the ignored output directories listed in the manifests "
                    "before running make check. In a local sibling worktree, copy them "
                    "from the populated checkout's output/ directory."
                ),
            )
        )

    return {
        "ok": not findings,
        "missing_artifacts": missing_artifacts,
        "findings": [asdict(finding) for finding in findings],
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render a concise human-readable preflight report."""

    lines = ["# Local Test Environment Preflight", ""]
    if report["ok"]:
        lines.append("All local maintainer-gate prerequisites are present.")
        return "\n".join(lines)

    lines.append("Local prerequisites are missing:")
    lines.append("")
    for finding in report["findings"]:
        lines.append(f"- `{finding['check']}`: {finding['message']}")
        lines.append(f"  Remediation: {finding['remediation']}")
    if report["missing_artifacts"]:
        lines.extend(["", "Missing frozen artifacts:"])
        for artifact in report["missing_artifacts"]:
            lines.append(f"- `{artifact}`")
    return "\n".join(lines)


def main() -> int:
    """Run the local environment preflight."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    report = check_environment()
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
