"""Restore ignored frozen eval artifacts into the current worktree.

The frozen eval manifests are tracked, but the referenced `output/` artifacts
are intentionally ignored because they are large runtime products. In the
standard local worktree layout, this command can copy the required artifact
directories from the populated main checkout into the current worktree so
`make check` can verify hashes without manual file hunting.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIR = REPO_ROOT / "config" / "eval_manifests"


@dataclass(frozen=True)
class RestoreResult:
    """One restored or missing frozen output directory."""

    artifact_dir: str
    source: str
    destination: str
    status: str


def default_source_output_dir(repo_root: Path = REPO_ROOT) -> Path:
    """Infer the populated checkout's output directory for local worktrees."""

    if repo_root.parent.name == "worktrees":
        return repo_root.parent.parent / "output"
    return repo_root / "output"


def manifest_artifact_dirs(manifest_dir: Path = MANIFEST_DIR) -> list[str]:
    """Return unique output directories referenced by eval manifests."""

    artifact_dirs: set[str] = set()
    for manifest_path in sorted(manifest_dir.glob("*.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for variant in manifest.get("variants", []):
            artifact_dir = variant.get("artifact_dir")
            if artifact_dir:
                artifact_dirs.add(str(artifact_dir).removeprefix("output/"))
    return sorted(artifact_dirs)


def restore_outputs(
    *,
    source_output_dir: Path,
    destination_output_dir: Path,
    overwrite: bool = False,
) -> list[RestoreResult]:
    """Copy manifest-referenced output directories from source to destination."""

    results: list[RestoreResult] = []
    destination_output_dir.mkdir(parents=True, exist_ok=True)
    for artifact_dir in manifest_artifact_dirs():
        source = source_output_dir / artifact_dir
        destination = destination_output_dir / artifact_dir
        if not source.exists():
            status = "missing_source"
        elif destination.exists() and not overwrite:
            status = "already_present"
        else:
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source, destination)
            status = "restored"
        results.append(
            RestoreResult(
                artifact_dir=f"output/{artifact_dir}",
                source=str(source),
                destination=str(destination),
                status=status,
            )
        )
    return results


def render_markdown(results: list[RestoreResult]) -> str:
    """Render a concise restore report."""

    lines = [
        "# Frozen Output Restore",
        "",
        "| artifact_dir | status |",
        "|---|---|",
    ]
    for result in results:
        lines.append(f"| `{result.artifact_dir}` | `{result.status}` |")
    return "\n".join(lines)


def main() -> int:
    """Run the frozen-output restore command."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-output",
        type=Path,
        default=default_source_output_dir(),
        help="Populated output directory to copy frozen artifacts from.",
    )
    parser.add_argument(
        "--destination-output",
        type=Path,
        default=REPO_ROOT / "output",
        help="Output directory in the current worktree.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    results = restore_outputs(
        source_output_dir=args.source_output,
        destination_output_dir=args.destination_output,
        overwrite=args.overwrite,
    )
    if args.format == "json":
        print(json.dumps([result.__dict__ for result in results], indent=2))
    else:
        print(render_markdown(results))
    return 1 if any(result.status == "missing_source" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
