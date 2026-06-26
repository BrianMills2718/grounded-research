"""Tests for the Tyler requirements YAML snapshot."""

from __future__ import annotations

from scripts.sync_tyler_requirements_yaml import (
    build_yaml_model,
    check_yaml,
    validate_model,
)


def test_tyler_requirements_yaml_contains_all_rows() -> None:
    """YAML model should represent every current Tyler registry row."""
    model = build_yaml_model()

    assert model["schema_version"] == 1
    assert model["source_policy"] == "synchronized_from_markdown_ledger_until_yaml_cutover"
    assert model["summary"]["requirements"] == 36
    assert len(model["requirements"]) == 36
    assert {row["id"] for row in model["requirements"]}


def test_tyler_requirements_yaml_declares_required_evidence() -> None:
    """Every row should declare evidence requirements from its class policy."""
    model = build_yaml_model()

    assert validate_model(model) == []
    for row in model["requirements"]:
        assert row["required_anchor_statuses"]
        assert row["required_evidence_kinds"] or row["required_any_evidence_kinds"]


def test_tyler_requirements_yaml_snapshot_is_current() -> None:
    """Tracked YAML should match the current ledger-derived model."""
    ok, message, findings = check_yaml()

    assert ok, message
    assert findings == []


def test_tyler_requirements_yaml_rejects_missing_runtime_test() -> None:
    """Runtime rows should not satisfy policy with source evidence only."""
    model = build_yaml_model()
    row = next(item for item in model["requirements"] if item["requirement_class"] == "runtime_behavior")
    row["evidence_kinds"] = ["local_source"]

    findings = validate_model(model)

    assert f"{row['id']}:missing_evidence_kind:local_test" in findings
