"""Check that production and script code carries explicit docstrings."""

from __future__ import annotations

import ast
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_ROOTS = ("src", "scripts")


@dataclass(frozen=True)
class MissingDocstring:
    """Location of one module, class, or function without a docstring."""

    path: Path
    kind: str
    name: str
    line: int

    def render(self) -> str:
        """Render the finding in grep-friendly path:line form."""
        return f"{self.path}:{self.line}: {self.kind} {self.name} is missing a docstring"


def _python_files(roots: Iterable[Path]) -> list[Path]:
    """Return all Python files below the requested audit roots."""
    files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            files.append(root)
        elif root.is_dir():
            files.extend(sorted(root.rglob("*.py")))
    return sorted(files)


def _missing_docstrings(path: Path) -> list[MissingDocstring]:
    """Collect docstring findings for one Python source file."""
    tree = ast.parse(path.read_text(), filename=str(path))
    missing: list[MissingDocstring] = []
    if ast.get_docstring(tree) is None:
        missing.append(MissingDocstring(path, "module", "<module>", 1))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            if ast.get_docstring(node) is None:
                missing.append(
                    MissingDocstring(path, type(node).__name__, node.name, node.lineno)
                )
    return missing


def check_docstrings(roots: Iterable[Path]) -> list[MissingDocstring]:
    """Return all missing docstrings below the requested roots."""
    findings: list[MissingDocstring] = []
    for path in _python_files(roots):
        findings.extend(_missing_docstrings(path))
    return findings


def main() -> int:
    """Run the docstring checker CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roots",
        nargs="*",
        type=Path,
        default=[Path(root) for root in DEFAULT_ROOTS],
        help="Files or directories to audit. Defaults to src/ and scripts/.",
    )
    args = parser.parse_args()

    findings = check_docstrings(args.roots)
    if findings:
        for finding in findings:
            print(finding.render())
        print(f"{len(findings)} missing docstring(s).")
        return 1
    print("All checked modules, classes, and functions have docstrings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
