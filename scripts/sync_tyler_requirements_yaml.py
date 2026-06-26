"""Generate or verify the YAML Tyler requirements source snapshot.

This YAML file is the structured requirements surface for maintainers. For this
slice it is synchronized from the current Markdown ledger and coverage read
model; a later cutover can invert ownership and generate Markdown from YAML.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.sync_tyler_registry import build_registry  # noqa: E402

YAML_PATH = Path("docs/tyler_requirements.yaml")


class NoAliasSafeDumper(yaml.SafeDumper):
    """YAML dumper that avoids anchors for repeated small policy lists."""

    def ignore_aliases(self, data: Any) -> bool:
        """Disable YAML aliases so generated files remain readable and diffable."""
        return True


EVIDENCE_POLICY: dict[str, dict[str, Any]] = {
    "ambiguity": {
        "required_anchor_statuses": ["line_level", "explicit_exception"],
        "required_any_evidence_kinds": [["doc", "local_source", "prompt_template", "tyler_source"]],
    },
    "doc_status": {
        "required_anchor_statuses": ["line_level", "explicit_exception"],
        "required_evidence_kinds": ["doc"],
    },
    "extension": {
        "required_anchor_statuses": ["line_level", "explicit_exception"],
        "required_any_evidence_kinds": [["doc", "local_source"]],
    },
    "model_config": {
        "required_anchor_statuses": ["line_level", "explicit_exception"],
        "required_any_evidence_kinds": [
            ["config", "local_source"],
            ["local_test", "runtime_artifact", "shared_infra_source"],
        ],
    },
    "operational_watch": {
        "required_anchor_statuses": ["line_level", "explicit_exception"],
        "required_evidence_kinds": ["runtime_artifact"],
        "required_any_evidence_kinds": [["config", "local_source"]],
    },
    "output_artifact": {
        "required_anchor_statuses": ["line_level", "explicit_exception"],
        "required_evidence_kinds": ["runtime_artifact"],
        "required_any_evidence_kinds": [["local_source", "local_test"]],
    },
    "prompt_template": {
        "required_anchor_statuses": ["line_level", "explicit_exception"],
        "required_evidence_kinds": ["prompt_template", "local_test"],
    },
    "provider_behavior": {
        "required_anchor_statuses": ["line_level", "explicit_exception"],
        "required_evidence_kinds": ["local_test"],
        "required_any_evidence_kinds": [["shared_infra_source", "shared_infra_test"]],
    },
    "runtime_behavior": {
        "required_anchor_statuses": ["line_level", "explicit_exception"],
        "required_evidence_kinds": ["local_source", "local_test"],
    },
    "schema_contract": {
        "required_anchor_statuses": ["line_level", "explicit_exception"],
        "required_evidence_kinds": ["local_source", "local_test"],
    },
}


def _requirement_yaml_row(row: dict[str, Any]) -> dict[str, Any]:
    """Convert one registry requirement into the YAML row shape."""

    evidence = sorted(row["evidence"], key=lambda item: (item["kind"], item["target"], item.get("symbol") or ""))
    evidence_kinds = sorted({item["kind"] for item in evidence})
    policy = EVIDENCE_POLICY[row["requirement_class"]]
    return {
        "id": row["requirement_id"],
        "requirement_class": row["requirement_class"],
        "closure_status": row["closure_status"],
        "evidence_grade": row["evidence_grade"],
        "anchor_status": row["anchor_status"],
        "tyler_sources": row["tyler_sources"],
        "owner": row["owner"],
        "severity": row["severity"],
        "evidence_kinds": evidence_kinds,
        "required_evidence_kinds": policy.get("required_evidence_kinds", []),
        "required_any_evidence_kinds": policy.get("required_any_evidence_kinds", []),
        "required_anchor_statuses": policy["required_anchor_statuses"],
        "evidence": evidence,
        "findings": row["findings"],
        "adversarial_notes": row["adversarial_notes"],
    }


def build_yaml_model() -> dict[str, Any]:
    """Build the stable YAML requirements model from the registry snapshot."""

    registry = build_registry()
    return {
        "schema_version": 1,
        "source_policy": "synchronized_from_markdown_ledger_until_yaml_cutover",
        "source_files": registry["source_files"],
        "summary": registry["summary"],
        "evidence_policy": EVIDENCE_POLICY,
        "requirements": [_requirement_yaml_row(row) for row in registry["requirements"]],
    }


def _yaml_text(model: dict[str, Any]) -> str:
    """Render canonical YAML for the requirements file."""

    return (
        yaml.dump(
            model,
            Dumper=NoAliasSafeDumper,
            sort_keys=False,
            allow_unicode=False,
            width=100,
        )
        + "\n"
    )


def write_yaml() -> None:
    """Write the YAML requirements snapshot."""

    (REPO_ROOT / YAML_PATH).write_text(_yaml_text(build_yaml_model()), encoding="utf-8")


def load_yaml() -> dict[str, Any]:
    """Load the tracked YAML requirements file."""

    return yaml.safe_load((REPO_ROOT / YAML_PATH).read_text(encoding="utf-8"))


def validate_model(model: dict[str, Any]) -> list[str]:
    """Validate the YAML model against the declared evidence policy."""

    findings: list[str] = []
    requirements = model.get("requirements", [])
    ids = [row.get("id") for row in requirements]
    if len(ids) != len(set(ids)):
        findings.append("duplicate_requirement_ids")
    for row in requirements:
        requirement_id = row["id"]
        requirement_class = row["requirement_class"]
        policy = model["evidence_policy"].get(requirement_class)
        if policy is None:
            findings.append(f"{requirement_id}:unknown_requirement_class:{requirement_class}")
            continue
        anchor_status = row["anchor_status"]
        if anchor_status not in policy["required_anchor_statuses"]:
            findings.append(f"{requirement_id}:anchor_status:{anchor_status}")
        evidence_kinds = set(row.get("evidence_kinds", []))
        for kind in policy.get("required_evidence_kinds", []):
            if kind not in evidence_kinds:
                findings.append(f"{requirement_id}:missing_evidence_kind:{kind}")
        for group in policy.get("required_any_evidence_kinds", []):
            if not evidence_kinds.intersection(group):
                expected = "|".join(group)
                findings.append(f"{requirement_id}:missing_any_evidence_kind:{expected}")
        if row.get("findings"):
            findings.append(f"{requirement_id}:coverage_findings_present")
    return findings


def check_yaml() -> tuple[bool, str, list[str]]:
    """Check whether tracked YAML is current and satisfies its policy."""

    path = REPO_ROOT / YAML_PATH
    if not path.exists():
        return False, f"Missing YAML requirements snapshot: {YAML_PATH}", []

    expected = _yaml_text(build_yaml_model())
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        return (
            False,
            "YAML requirements snapshot is stale: run python scripts/sync_tyler_requirements_yaml.py --write",
            [],
        )

    findings = validate_model(load_yaml())
    if findings:
        return False, "YAML requirements evidence policy findings found.", findings
    return True, "YAML requirements snapshot is current and policy-clean.", []


def main() -> int:
    """Run YAML sync/check command."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write YAML requirements snapshot")
    parser.add_argument("--check", action="store_true", help="Fail if YAML snapshot is stale or invalid")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()

    if args.write:
        write_yaml()
        result: dict[str, Any] = {"ok": True, "message": f"Wrote {YAML_PATH}", "findings": []}
    elif args.check:
        ok, message, findings = check_yaml()
        result = {"ok": ok, "message": message, "findings": findings}
    else:
        result = build_yaml_model()

    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    elif "message" in result:
        print(result["message"])
        for finding in result.get("findings", []):
            print(f"- {finding}")
    else:
        print(_yaml_text(result), end="")

    if args.check and not result["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
