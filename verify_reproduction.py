"""Check model tests, saved numerical results, and notebook Python 3.10 syntax.

This does not validate external article sources, economic assumptions, or rights.
Run from the repository root: python3 verify_reproduction.py
"""
from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
CODE = ROOT / "code"


def main() -> int:
    sys.path.insert(0, str(CODE))
    suite = unittest.defaultTestLoader.discover(str(CODE), pattern="test_model.py")
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful() or outcome.skipped:
        return 1

    matched = []
    with tempfile.TemporaryDirectory(prefix="disc-model-") as directory:
        destination = Path(directory)
        subprocess.run(
            [sys.executable, str(CODE / "model.py"), "--config",
             str(CODE / "scenarios.json"), "--out", str(destination)],
            check=True, capture_output=True, text=True,
        )
        experiments = importlib.import_module("experiments")
        experiments.run(out=destination)
        for name in ("results.json", "policies.csv", "yearly.csv",
                     "sensitivity.json", "natural_migration.csv", "simple_frontier.csv"):
            # CSV writers can use OS-specific line endings; compare decoded text.
            expected = (ROOT / "results" / name).read_text(encoding="utf-8")
            actual = (destination / name).read_text(encoding="utf-8")
            if actual != expected:
                raise RuntimeError(f"Saved result differs: {name}")
            matched.append(name)

    notebook = json.loads((ROOT / "analysis.ipynb").read_text(encoding="utf-8"))
    code_cells = 0
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]), feature_version=(3, 10))
            code_cells += 1
    for path in CODE.glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 10))
    print(json.dumps({
        "model_tests_passed": outcome.testsRun,
        "skipped": len(outcome.skipped),
        "saved_result_files_matched": matched,
        "notebook_code_cells_syntax_checked": code_cells,
        "syntax_target": "Python 3.10",
        "note": "Syntax compatibility is not execution on Python 3.10.",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
