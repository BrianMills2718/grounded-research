"""Generate or verify the structured Tyler requirement registry snapshot.

The current authoring surface is still the Markdown ledger. This script creates
a stable normalized JSON snapshot from the coverage read model so reviewers and
agents can diff structured requirement state directly. It is an explicit
one-way generation policy until the project is ready to invert ownership and
generate Markdown from structured data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_tyler_coverage import build_coverage_report  # noqa: E402

REGISTRY_PATH = Path("docs/tyler_requirements_registry.json")


def build_registry() -> dict[str, Any]:
    """Build the stable Tyler registry snapshot from the coverage read model."""

    coverage = build_coverage_report()
    requirements = sorted(
        coverage["requirements"],
        key=lambda row: row["requirement_id"],
    )
    return {
        "schema_version": 1,
        "source_policy": "generated_from_markdown_ledger",
        "source_files": coverage["sources"],
        "summary": coverage["summary"],
        "by_grade": coverage["by_grade"],
        "by_requirement_class": coverage["by_requirement_class"],
        "by_anchor_status": coverage["by_anchor_status"],
        "requirements": requirements,
    }


def _registry_text(registry: dict[str, Any]) -> str:
    """Render canonical JSON for the registry file."""

    return json.dumps(registry, indent=2, sort_keys=True) + "\n"


def write_registry() -> None:
    """Write the registry snapshot."""

    (REPO_ROOT / REGISTRY_PATH).write_text(_registry_text(build_registry()), encoding="utf-8")


def check_registry() -> tuple[bool, str]:
    """Check whether the tracked registry snapshot matches current ledger state."""

    expected = _registry_text(build_registry())
    path = REPO_ROOT / REGISTRY_PATH
    if not path.exists():
        return False, f"Missing registry snapshot: {REGISTRY_PATH}"
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        return False, "Registry snapshot is stale: run python scripts/sync_tyler_registry.py --write"
    return True, "Registry snapshot is current."


def main() -> int:
    """Run registry sync/check command."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write registry snapshot")
    parser.add_argument("--check", action="store_true", help="Fail if registry snapshot is stale")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()

    if args.write:
        write_registry()
        result = {"ok": True, "message": f"Wrote {REGISTRY_PATH}"}
    elif args.check:
        ok, message = check_registry()
        result = {"ok": ok, "message": message}
    else:
        result = build_registry()

    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    elif "message" in result:
        print(result["message"])
    else:
        print(_registry_text(result), end="")

    if args.check and not result["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
