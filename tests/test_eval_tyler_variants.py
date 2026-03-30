"""Tests for the frozen Tyler-variant evaluation harness."""

from __future__ import annotations

from pathlib import Path

from scripts import eval_tyler_variants as eval_module


def test_manifest_hashes_match_current_frozen_outputs() -> None:
    """The checked-in manifest must match the saved frozen artifacts."""
    manifest = eval_module.load_manifest()
    eval_module.verify_manifest(manifest)


def test_build_precomputed_payloads_repeats_each_variant() -> None:
    """The harness should emit one shared input and repeated per-variant outputs."""
    manifest = eval_module.load_manifest()

    inputs, outputs = eval_module.build_precomputed_payloads(manifest, repeats=3)

    assert len(inputs) == 1
    assert inputs[0]["id"] == "ubi_current_evidence"
    assert len(outputs) == len(manifest.variants) * 3
    assert {item["variant_name"] for item in outputs} == {"tyler_literal", "calibrated_legacy"}
    assert {item["replicate"] for item in outputs} == {0, 1, 2}
    assert all("commit_anchor" in item["provenance"] for item in outputs)


def test_verify_manifest_fails_loud_on_hash_mismatch(tmp_path: Path) -> None:
    """Hash drift in the frozen manifest should fail loudly."""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        """
{
  "experiment_name": "bad",
  "question": "q",
  "variants": [
    {
      "name": "tyler_literal",
      "label": "bad",
      "commit_anchor": "abc123",
      "artifact_dir": "output/tyler_literal_parity_ubi_reanchor_v8",
      "files": {
        "report_md": {
          "path": "output/tyler_literal_parity_ubi_reanchor_v8/report.md",
          "sha256": "deadbeef"
        }
      }
    },
    {
      "name": "calibrated_legacy",
      "label": "bad",
      "commit_anchor": "def456",
      "artifact_dir": "output/ubi_dense_dedup_eval",
      "files": {
        "report_md": {
          "path": "output/ubi_dense_dedup_eval/report.md",
          "sha256": "deadbeef"
        }
      }
    }
  ]
}
        """.strip()
    )

    manifest = eval_module.load_manifest(manifest_path)
    try:
        eval_module.verify_manifest(manifest)
    except ValueError as exc:
        assert "hash mismatch" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected manifest verification to fail loudly")
