"""Tests for frozen output artifact restoration."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.restore_frozen_outputs import (
    default_source_output_dir,
    manifest_artifact_dirs,
    restore_outputs,
)


def test_default_source_output_dir_uses_parent_checkout_for_worktrees() -> None:
    """Worktree checkouts should copy artifacts from the populated parent repo."""
    repo_root = Path("/repo/worktrees/branch")

    assert default_source_output_dir(repo_root) == Path("/repo/output")


def test_manifest_artifact_dirs_reads_unique_variant_dirs(tmp_path: Path) -> None:
    """Manifest parsing should return the output dirs needed by frozen evals."""
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    (manifest_dir / "example.json").write_text(
        json.dumps(
            {
                "variants": [
                    {"artifact_dir": "output/a"},
                    {"artifact_dir": "output/b"},
                    {"artifact_dir": "output/a"},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert manifest_artifact_dirs(manifest_dir) == ["a", "b"]


def test_restore_outputs_copies_manifest_dirs(tmp_path: Path, monkeypatch) -> None:
    """Restore should copy only manifest-referenced output directories."""
    source_output = tmp_path / "source" / "output"
    destination_output = tmp_path / "dest" / "output"
    (source_output / "a").mkdir(parents=True)
    (source_output / "a" / "report.md").write_text("report", encoding="utf-8")

    monkeypatch.setattr("scripts.restore_frozen_outputs.manifest_artifact_dirs", lambda: ["a"])

    results = restore_outputs(
        source_output_dir=source_output,
        destination_output_dir=destination_output,
    )

    assert results[0].status == "restored"
    assert (destination_output / "a" / "report.md").read_text(encoding="utf-8") == "report"
