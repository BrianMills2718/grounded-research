"""Verify tracked raw Tyler source packet line counts and hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class TylerSourceExpected:
    """Expected reproducibility metadata for one raw Tyler source file."""

    path: str
    lines: int
    sha256: str


@dataclass(frozen=True)
class TylerSourceActual:
    """Observed reproducibility metadata for one raw Tyler source file."""

    path: str
    expected_lines: int
    actual_lines: int | None
    expected_sha256: str
    actual_sha256: str | None
    exists: bool
    ok: bool


EXPECTED_SOURCES = (
    TylerSourceExpected(
        path="2026_0325_tyler_feedback/1. V1_Build_Plan_Step_By_Step.md",
        lines=248,
        sha256="962afd0e2fc9bce4c7aee81ede0b32a9797297b3a34d6270f8096ee57033f95a",
    ),
    TylerSourceExpected(
        path="2026_0325_tyler_feedback/2. V1_DESIGN.md",
        lines=347,
        sha256="6c4f5c3e1ab631030da568a2a2b28e940a93de8a6eef172c9f332ba95f9125bb",
    ),
    TylerSourceExpected(
        path="2026_0325_tyler_feedback/3. V1_SCHEMAS.md",
        lines=619,
        sha256="6c89eeffd1233d66e61d513dc6c0fa2b437a47beaf96fdc36eb1d0f9717d0881",
    ),
    TylerSourceExpected(
        path="2026_0325_tyler_feedback/4. V1_PROMPTS.md",
        lines=1163,
        sha256="d53aa8cb43267451848486b4de7b5425de5a751b08cdcbd7000f5e00b5befa41",
    ),
)


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest for a file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _line_count(path: Path) -> int:
    """Return newline-delimited line count for a text file."""

    return len(path.read_text(encoding="utf-8").splitlines())


def build_source_manifest_report() -> dict[str, Any]:
    """Build raw Tyler source reproducibility report."""

    rows: list[TylerSourceActual] = []
    for expected in EXPECTED_SOURCES:
        path = ROOT / expected.path
        if not path.exists():
            rows.append(
                TylerSourceActual(
                    path=expected.path,
                    expected_lines=expected.lines,
                    actual_lines=None,
                    expected_sha256=expected.sha256,
                    actual_sha256=None,
                    exists=False,
                    ok=False,
                )
            )
            continue
        actual_lines = _line_count(path)
        actual_sha256 = _sha256(path)
        rows.append(
            TylerSourceActual(
                path=expected.path,
                expected_lines=expected.lines,
                actual_lines=actual_lines,
                expected_sha256=expected.sha256,
                actual_sha256=actual_sha256,
                exists=True,
                ok=actual_lines == expected.lines and actual_sha256 == expected.sha256,
            )
        )
    return {
        "sources": ["docs/TYLER_SOURCE_MANIFEST.md", *[item.path for item in EXPECTED_SOURCES]],
        "summary": {
            "files": len(rows),
            "total_expected_lines": sum(item.lines for item in EXPECTED_SOURCES),
            "failures": sum(1 for row in rows if not row.ok),
        },
        "files": [asdict(row) for row in rows],
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render a raw Tyler source manifest check."""

    lines = [
        "# Tyler Source Manifest Check",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ]
    for key, value in report["summary"].items():
        lines.append(f"| {key} | {value} |")

    lines.extend(["", "## Files", ""])
    lines.append("| file | expected lines | actual lines | ok |")
    lines.append("|---|---:|---:|---|")
    for row in report["files"]:
        actual_lines = "" if row["actual_lines"] is None else row["actual_lines"]
        lines.append(
            f"| `{row['path']}` | {row['expected_lines']} | {actual_lines} | {row['ok']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """Run the Tyler source manifest checker."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args()

    report = build_source_manifest_report()
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report))
    if args.fail_on_findings and report["summary"]["failures"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
