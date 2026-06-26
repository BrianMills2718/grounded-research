"""Check Tyler requirement traceability across docs, code, and tests.

The Tyler compliance surface is currently maintained in Markdown. This script
turns the active ledger and matrices into a compact machine-checkable view so
maintainers can see which requirements have code/test evidence and which links
are broken or incomplete.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = Path("docs/TYLER_SPEC_GAP_LEDGER.md")
AUDIT_MATRIX_PATH = Path("docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md")
REVIEW_MATRIX_PATH = Path("docs/TYLER_SYSTEMATIC_REVIEW_MATRIX.md")

PATH_PREFIXES = (
    "README.md",
    "config/",
    "docs/",
    "engine.py",
    "prompts/",
    "scripts/",
    "src/",
    "tests/",
    "2026_0325_tyler_feedback/",
    "llm_client/",
    "open_web_retrieval/",
    "prompt_eval/",
)
TYLER_SOURCE_ALIASES = {
    "1. V1_Build_Plan_Step_By_Step.md": "2026_0325_tyler_feedback/1. V1_Build_Plan_Step_By_Step.md",
    "1. V1_Build_Plan_Step_By_Step (1).md": "2026_0325_tyler_feedback/1. V1_Build_Plan_Step_By_Step.md",
    "2. V1_DESIGN.md": "2026_0325_tyler_feedback/2. V1_DESIGN.md",
    "3. V1_SCHEMAS.md": "2026_0325_tyler_feedback/3. V1_SCHEMAS.md",
    "3. V1_SCHEMAS (1).md": "2026_0325_tyler_feedback/3. V1_SCHEMAS.md",
    "4. V1_PROMPTS.md": "2026_0325_tyler_feedback/4. V1_PROMPTS.md",
    "4. V1_PROMPTS (1).md": "2026_0325_tyler_feedback/4. V1_PROMPTS.md",
}


@dataclass(frozen=True)
class TableRow:
    """One parsed Markdown table row keyed by its first column."""

    source: str
    key: str
    fields: dict[str, str]


@dataclass(frozen=True)
class Reference:
    """One filesystem or pytest reference extracted from a traceability row."""

    owner_id: str
    kind: str
    raw: str
    path: str
    symbol: str | None
    exists: bool


def _split_markdown_row(line: str) -> list[str]:
    """Split a simple Markdown table row while preserving inline code text."""

    cells: list[str] = []
    current: list[str] = []
    in_code = False
    for char in line.strip().strip("|"):
        if char == "`":
            in_code = not in_code
            current.append(char)
            continue
        if char == "|" and not in_code:
            cells.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    cells.append("".join(current).strip())
    return cells


def _parse_table(path: Path, key_column: str) -> list[TableRow]:
    """Parse the first-column-keyed Markdown table rows from a document."""

    full_path = ROOT / path
    lines = full_path.read_text(encoding="utf-8").splitlines()
    rows: list[TableRow] = []
    headers: list[str] | None = None
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = _split_markdown_row(line)
        if not cells:
            continue
        if all(set(cell) <= {"-"} for cell in cells):
            continue
        if key_column in cells:
            headers = cells
            continue
        if headers is None or len(cells) != len(headers):
            continue
        fields = dict(zip(headers, cells, strict=True))
        key = fields.get(key_column, "").strip("` ")
        if key:
            rows.append(TableRow(source=str(path), key=key, fields=fields))
    return rows


def _code_spans(text: str) -> list[str]:
    """Return inline-code spans from Markdown text."""

    return [match.group(1).strip() for match in re.finditer(r"`([^`]+)`", text)]


def _test_refs(text: str) -> list[str]:
    """Extract pytest-style references from free text."""

    pattern = (
        r"(?:(?:llm_client|open_web_retrieval|prompt_eval)/)?"
        r"tests/[A-Za-z0-9_./-]+\.py(?:::[A-Za-z_][A-Za-z0-9_]*)?"
    )
    return re.findall(pattern, text)


def _normalize_ref(raw: str) -> tuple[str, str | None] | None:
    """Normalize a raw path/test reference to a repo-relative path and symbol."""

    candidate = TYLER_SOURCE_ALIASES.get(raw, raw)
    if "::" in candidate:
        path, symbol = candidate.split("::", 1)
    else:
        path, symbol = candidate, None
    path = path.strip()
    if not path.startswith(PATH_PREFIXES):
        return None
    return path, symbol


def _reference_exists(path: str, symbol: str | None) -> bool:
    """Check whether a path and optional pytest function reference exists."""

    if path.startswith(("llm_client/", "open_web_retrieval/", "prompt_eval/")):
        return True
    full_path = ROOT / path
    if not full_path.exists():
        return False
    if symbol is None:
        return True
    text = full_path.read_text(encoding="utf-8")
    pattern = rf"(def|class)\s+{re.escape(symbol)}(\s*\(|[:\(])"
    return re.search(pattern, text) is not None


def _extract_references(row: TableRow) -> list[Reference]:
    """Extract filesystem and test references from a ledger row."""

    text = " ".join(row.fields.values())
    raw_refs: set[str] = set()
    for raw in _code_spans(text) + _test_refs(text):
        if " " in raw and not raw.startswith("2026_0325_tyler_feedback/"):
            raw_refs.update(part for part in raw.split() if _normalize_ref(part) is not None)
        elif _normalize_ref(raw) is not None:
            raw_refs.add(raw)
        else:
            raw_refs.add(raw)
    refs: list[Reference] = []
    for raw in sorted(raw_refs):
        normalized = _normalize_ref(raw)
        if normalized is None:
            continue
        path, symbol = normalized
        is_external = path.startswith(("llm_client/", "open_web_retrieval/", "prompt_eval/"))
        kind = "test" if "/tests/" in path or path.startswith("tests/") else "source"
        if is_external:
            kind = f"external_{kind}"
        refs.append(
            Reference(
                owner_id=row.key,
                kind=kind,
                raw=raw,
                path=path,
                symbol=symbol,
                exists=_reference_exists(path, symbol),
            )
        )
    return refs


def _ids_from_field(text: str) -> list[str]:
    """Extract ledger-like identifiers from an audit/review matrix field."""

    if text.lower().strip() == "none":
        return []
    return re.findall(r"`?([A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+-\d{3})`?", text)


def build_report() -> dict[str, Any]:
    """Build a structured traceability report from active Tyler docs."""

    ledger_rows = _parse_table(LEDGER_PATH, "spec_id")
    audit_rows = _parse_table(AUDIT_MATRIX_PATH, "audit_unit_id")
    review_rows = _parse_table(REVIEW_MATRIX_PATH, "review_id")
    ledger_by_id = {row.key: row for row in ledger_rows}

    refs = [ref for row in ledger_rows for ref in _extract_references(row)]
    refs_by_owner: dict[str, list[Reference]] = {}
    for ref in refs:
        refs_by_owner.setdefault(ref.owner_id, []).append(ref)

    audit_missing_ledger: list[dict[str, str]] = []
    for row in audit_rows:
        for ledger_id in _ids_from_field(row.fields.get("ledger_rows", "")):
            if ledger_id not in ledger_by_id:
                audit_missing_ledger.append({"audit_unit_id": row.key, "ledger_id": ledger_id})

    review_missing_ledger: list[dict[str, str]] = []
    for row in review_rows:
        for ledger_id in _ids_from_field(row.fields.get("current source of truth", "")):
            if ledger_id not in ledger_by_id:
                review_missing_ledger.append({"review_id": row.key, "ledger_id": ledger_id})

    ledger_without_tests: list[str] = []
    ledger_without_source_refs: list[str] = []
    for row in ledger_rows:
        owner_refs = refs_by_owner.get(row.key, [])
        next_action = row.fields.get("next_action", "")
        classification = row.fields.get("classification", "")
        needs_test_evidence = next_action == "verified_fixed" and classification != "stale_doc"
        if needs_test_evidence and not any(ref.kind == "test" for ref in owner_refs):
            ledger_without_tests.append(row.key)
        if not any(ref.kind == "source" for ref in owner_refs):
            ledger_without_source_refs.append(row.key)

    missing_refs = [
        {
            "owner_id": ref.owner_id,
            "kind": ref.kind,
            "raw": ref.raw,
            "path": ref.path,
            "symbol": ref.symbol,
        }
        for ref in refs
        if not ref.exists
    ]

    by_next_action: dict[str, int] = {}
    by_classification: dict[str, int] = {}
    for row in ledger_rows:
        by_next_action[row.fields.get("next_action", "")] = (
            by_next_action.get(row.fields.get("next_action", ""), 0) + 1
        )
        by_classification[row.fields.get("classification", "")] = (
            by_classification.get(row.fields.get("classification", ""), 0) + 1
        )

    open_rows = [
        row.key
        for row in ledger_rows
        if row.fields.get("next_action") not in {"verified_fixed", "document_local_interpretation"}
    ]

    return {
        "sources": [
            str(LEDGER_PATH),
            str(AUDIT_MATRIX_PATH),
            str(REVIEW_MATRIX_PATH),
        ],
        "summary": {
            "ledger_rows": len(ledger_rows),
            "audit_units": len(audit_rows),
            "review_lanes": len(review_rows),
            "references": len(refs),
            "missing_references": len(missing_refs),
            "audit_missing_ledger_links": len(audit_missing_ledger),
            "review_missing_ledger_links": len(review_missing_ledger),
            "verified_rows_without_test_refs": len(ledger_without_tests),
            "rows_without_source_refs": len(ledger_without_source_refs),
        },
        "by_next_action": by_next_action,
        "by_classification": by_classification,
        "open_rows": open_rows,
        "missing_references": missing_refs,
        "audit_missing_ledger_links": audit_missing_ledger,
        "review_missing_ledger_links": review_missing_ledger,
        "verified_rows_without_test_refs": ledger_without_tests,
        "rows_without_source_refs": ledger_without_source_refs,
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render a human-readable Markdown traceability report."""

    lines = [
        "# Tyler Traceability Report",
        "",
        "> Generated from active ledger/matrix docs. Do not edit this output as source of truth.",
        "",
        "## Sources",
        "",
    ]
    lines.extend(f"- `{source}`" for source in report["sources"])
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| Metric | Count |",
            "|---|---:|",
        ]
    )
    for key, value in report["summary"].items():
        lines.append(f"| {key} | {value} |")

    lines.extend(["", "## Ledger Status", "", "| next_action | rows |", "|---|---:|"])
    for key, value in sorted(report["by_next_action"].items()):
        lines.append(f"| `{key}` | {value} |")

    lines.extend(["", "## Classification", "", "| classification | rows |", "|---|---:|"])
    for key, value in sorted(report["by_classification"].items()):
        lines.append(f"| `{key}` | {value} |")

    sections = [
        ("Open Rows", "open_rows"),
        ("Missing References", "missing_references"),
        ("Audit Units Pointing At Missing Ledger Rows", "audit_missing_ledger_links"),
        ("Review Lanes Pointing At Missing Ledger Rows", "review_missing_ledger_links"),
        ("Verified Rows Without Test References", "verified_rows_without_test_refs"),
        ("Rows Without Source References", "rows_without_source_refs"),
    ]
    for title, key in sections:
        lines.extend(["", f"## {title}", ""])
        values = report[key]
        if not values:
            lines.append("None.")
            continue
        for value in values:
            lines.append(f"- `{value}`" if isinstance(value, str) else f"- `{json.dumps(value)}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """Run the traceability check CLI."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit non-zero when broken links or missing matrix cross-links are found.",
    )
    args = parser.parse_args()

    report = build_report()
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown(report))

    if args.fail_on_issues:
        failing_counts = [
            report["summary"]["missing_references"],
            report["summary"]["audit_missing_ledger_links"],
            report["summary"]["review_missing_ledger_links"],
        ]
        if any(count > 0 for count in failing_counts):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
