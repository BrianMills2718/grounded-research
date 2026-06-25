"""Tests for the structured Tyler registry snapshot."""

from __future__ import annotations

from scripts.sync_tyler_registry import build_registry, check_registry


def test_tyler_registry_contains_all_requirements() -> None:
    """Registry snapshot data should expose all current Tyler rows."""
    registry = build_registry()

    assert registry["schema_version"] == 1
    assert registry["source_policy"] == "generated_from_markdown_ledger"
    assert registry["summary"]["requirements"] == 36
    assert len(registry["requirements"]) == 36
    assert registry["requirements"][0]["requirement_id"] == "AMB-S2-REASONING-001"


def test_tyler_registry_snapshot_is_current() -> None:
    """Tracked registry JSON should match the current ledger-derived model."""
    ok, message = check_registry()

    assert ok, message
