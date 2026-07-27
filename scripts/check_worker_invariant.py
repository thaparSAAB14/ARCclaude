#!/usr/bin/env python
"""Enforce the worker's stdlib-only invariant.

ARCclaude's worker runs on ArcGIS Pro's locked `arcgispro-py3` environment,
which we never modify: no pip installs, no env cloning, no admin rights. That
promise only holds while worker-side code imports nothing beyond the standard
library and `arcpy` itself. A stray `import requests` would work fine on the
machine that added it and fail on every clean install, so CI checks it here
instead of leaving it to review.

Covers the worker package and the add-in's geoprocessing runner - both execute
inside Esri's Python.

Usage: python scripts/check_worker_invariant.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ALLOWED_NON_STDLIB = {"arcpy"}

ROOT = Path(__file__).resolve().parent.parent
SCAN_GLOBS = (
    "src/arcclaude/worker/**/*.py",
    "addin/**/Runner/*.pyt",
)
# Compiled/copied artifacts are duplicates of the sources above.
EXCLUDE_PARTS = {"bin", "obj", ".venv"}


def imported_top_level_modules(tree: ast.Module) -> set[str]:
    """Every top-level package name this module imports, at any nesting."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        # level > 0 is a relative import - always local, never third-party.
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def main() -> int:
    stdlib = set(sys.stdlib_module_names)
    files = sorted({
        p for pattern in SCAN_GLOBS for p in ROOT.glob(pattern)
        if not EXCLUDE_PARTS & set(p.relative_to(ROOT).parts)
    })
    if not files:
        print("check_worker_invariant: no worker files found - wrong directory?")
        return 1

    violations: list[str] = []
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            violations.append(f"{path.relative_to(ROOT)}: syntax error: {exc}")
            continue
        for module in sorted(imported_top_level_modules(tree)):
            if module in stdlib or module in ALLOWED_NON_STDLIB:
                continue
            violations.append(
                f"{path.relative_to(ROOT)}: imports '{module}', which is neither "
                f"standard library nor {sorted(ALLOWED_NON_STDLIB)}"
            )

    for path in files:
        print(f"  checked {path.relative_to(ROOT)}")

    if violations:
        print("\nWorker stdlib-only invariant VIOLATED:")
        for v in violations:
            print(f"  - {v}")
        print(
            "\nWorker code must run on Esri's untouched arcgispro-py3 environment.\n"
            "Move third-party dependencies to the server side (src/arcclaude/), or\n"
            "add the module to ALLOWED_NON_STDLIB only if ArcGIS Pro ships it."
        )
        return 1

    print(f"\nOK: {len(files)} worker file(s) import only the standard library + arcpy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
