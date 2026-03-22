#!/usr/bin/env python3
"""Validate machine-readable ADR invariants and emit a CI-ready checklist.

Usage:
  python scripts/check_adr_invariants.py --adr docs/adr/0004-agentic-verification-and-fail-loud-phase4.md
  python scripts/check_adr_invariants.py --adr docs/adr/*.md --strict

The script reads the `Machine-Readable Invariants` YAML block and verifies:
  1) structure is present and parseable,
  2) source-of-truth files exist,
  3) optional `checks` patterns are present in indicated files.

It exits non-zero only when explicit validation failures are detected and
`--strict` is enabled.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class InvariantCheck:
    """One required text-pattern check for a specific file."""

    file: str
    patterns: list[str]


@dataclass
class Invariant:
    """A parsed ADR invariant with its machine-readable fields."""

    adr_path: str
    invariant_id: str
    must_hold: str
    source_of_truth: list[str]
    checks: list[InvariantCheck]


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_yaml_block(text: str) -> str | None:
    marker = r"##\s+Machine-Readable Invariants"
    if not re.search(marker, text, re.IGNORECASE):
        return None
    match = re.search(
        marker + r"[\s\S]*?```(?:yaml)?\n([\s\S]*?)\n```",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).strip()


def _normalize_items(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    return [str(item).strip() for item in items if str(item).strip()]


def parse_invariants_from_adr(path: Path) -> list[Invariant]:
    text = _load_text(path)
    block = _extract_yaml_block(text)
    if not block:
        raise ValueError(f"Missing machine-readable invariants block in {path}")

    payload = yaml.safe_load(block)
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid invariants payload in {path}: expected dict root")

    raw_invariants = payload.get("invariants")
    if not isinstance(raw_invariants, list):
        raise ValueError(f"Invalid invariants payload in {path}: expected list")

    parsed: list[Invariant] = []
    for item in raw_invariants:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid invariant entry in {path}: {item!r}")

        invariant_id = str(item.get("id", "")).strip()
        must_hold = str(item.get("must_hold", "")).strip()
        source_of_truth = _normalize_items(item.get("source_of_truth"))
        checks: list[InvariantCheck] = []

        for check in item.get("checks", []):
            if not isinstance(check, dict):
                continue
            file_value = str(check.get("file", "")).strip()
            if not file_value:
                continue
            patterns = _normalize_items(check.get("must_include"))
            checks.append(InvariantCheck(file=file_value, patterns=patterns))

        if not invariant_id:
            raise ValueError(f"ADR invariant missing id in {path}")
        if not must_hold:
            raise ValueError(f"ADR invariant missing must_hold in {path}: {invariant_id}")
        if not source_of_truth:
            raise ValueError(f"ADR invariant missing source_of_truth in {path}: {invariant_id}")

        parsed.append(
            Invariant(
                adr_path=str(path),
                invariant_id=invariant_id,
                must_hold=must_hold,
                source_of_truth=source_of_truth,
                checks=checks,
            )
        )

    return parsed


def render_checklist(invariants: list[Invariant], root: Path, validate_patterns: bool) -> tuple[str, list[str]]:
    errors: list[str] = []
    lines = ["# ADR invariant checklist\n"]

    for inv in invariants:
        lines.append(f"- [ ] {inv.invariant_id}")
        lines.append(f"  - ADR: {inv.adr_path}")
        lines.append(f"  - Must hold: {inv.must_hold}")
        lines.append("  - Source of truth:")
        for source in inv.source_of_truth:
            source_path = (root / source).as_posix()
            lines.append(f"    - {source_path}")
            if not (root / source).exists():
                errors.append(f"Source file missing: {source_path}")

        if inv.checks:
            lines.append("  - Checks:")
            for check in inv.checks:
                for pattern in check.patterns:
                    if validate_patterns:
                        if not file_path_exists(root, check.file):
                            errors.append(f"Check file missing: {check.file}")
                        else:
                            text = _load_text(root / check.file)
                            if pattern not in text:
                                errors.append(
                                    f"Pattern missing for {inv.invariant_id}: '{pattern}' in {check.file}"
                                )
                            else:
                                lines.append(f"    - [ ] {check.file}: contains '{pattern}'")
                    else:
                        lines.append(f"    - [ ] {check.file}: contains '{pattern}'")

    return "\n".join(lines), errors


def file_path_exists(root: Path, candidate: str) -> bool:
    return (root / candidate).exists()


def gather_adrs(adr_paths: list[str]) -> list[Path]:
    root = Path.cwd()
    files: list[Path] = []
    for raw in adr_paths:
        for path in sorted(Path().glob(str(raw))):
            if path.name.endswith(".md"):
                files.append((root / path).resolve())
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in files:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return deduped


def validate_and_render(paths: list[Path], strict: bool, validate_patterns: bool) -> int:
    root = Path.cwd()
    all_invariants: list[Invariant] = []

    for adr_path in paths:
        if not adr_path.exists():
            print(f"Missing ADR file: {adr_path}", file=sys.stderr)
            if strict:
                return 2
            continue

        try:
            all_invariants.extend(parse_invariants_from_adr(adr_path))
        except ValueError as exc:
            print(f"{exc}", file=sys.stderr)
            if strict:
                return 2

    if not all_invariants:
        print("No ADR invariants found.", file=sys.stderr)
        return 0 if not strict else 2

    checklist, errors = render_checklist(all_invariants, root, validate_patterns)
    print(checklist)

    if errors:
        print("\nValidation issues:", file=sys.stderr)
        for issue in errors:
            print(f"  - {issue}", file=sys.stderr)
        return 2

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/validate ADR invariant checklists")
    parser.add_argument(
        "--adr",
        action="append",
        nargs="+",
        default=[],
        help="ADR markdown path or glob (can be passed multiple times).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat missing invariants or failed checks as hard failures.",
    )
    parser.add_argument(
        "--skip-pattern-checks",
        action="store_true",
        help="Emit checklist only; do not validate file content patterns.",
    )
    args = parser.parse_args()

    adr_args = [item for group in args.adr for item in group] if args.adr else ["docs/adr/*.md"]
    paths = gather_adrs(adr_args)
    return validate_and_render(paths, strict=args.strict, validate_patterns=not args.skip_pattern_checks)


if __name__ == "__main__":
    raise SystemExit(main())
