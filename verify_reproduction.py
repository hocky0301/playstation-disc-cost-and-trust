"""Check model tests, saved numerical results, and notebook syntax.

Saved results are compared by value, not by bytes: JSON is compared as
structure, CSV cell by cell. Numbers must agree within a relative tolerance of
1e-9 (math.isclose, abs_tol=0.0); strings must match exactly. This absorbs the
last-digit float differences between Python versions and still catches any
real change (a 0.01 oku-en difference, 1e6 yen, is orders of magnitude above
1e-9 relative for every saved value).

This does not validate external article sources, economic assumptions, or rights.
Run from the repository root: python3 verify_reproduction.py
It writes to a temporary directory only; the saved results are never overwritten.
"""
from __future__ import annotations

import ast
import csv
import importlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
CODE = ROOT / "code"

REL_TOL = 1e-9
ABS_TOL = 0.0
SYNTAX_TARGET = (3, 10)
EXPECTED_RESULT_FILES = ("results.json", "policies.csv", "yearly.csv",
                         "sensitivity.json", "natural_migration.csv", "simple_frontier.csv")


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def numbers_match(expected, actual) -> bool:
    if expected == actual:
        return True
    if not (math.isfinite(expected) and math.isfinite(actual)):
        return False
    return math.isclose(expected, actual, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def compare_json(expected, actual, where: str = "$") -> list[str]:
    """Return a list of differences; an empty list means the two match."""
    if is_number(expected) and is_number(actual):
        if numbers_match(expected, actual):
            return []
        return [f"{where}: {expected!r} != {actual!r}"]
    if type(expected) is not type(actual):
        return [f"{where}: type {type(expected).__name__} != {type(actual).__name__}"]
    if isinstance(expected, dict):
        problems = []
        for key in sorted(set(expected) | set(actual)):
            if key not in actual:
                problems.append(f"{where}.{key}: missing in new result")
            elif key not in expected:
                problems.append(f"{where}.{key}: not in saved result")
            else:
                problems.extend(compare_json(expected[key], actual[key], f"{where}.{key}"))
        return problems
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [f"{where}: length {len(expected)} != {len(actual)}"]
        problems = []
        for index, (e, a) in enumerate(zip(expected, actual)):
            problems.extend(compare_json(e, a, f"{where}[{index}]"))
        return problems
    return [] if expected == actual else [f"{where}: {expected!r} != {actual!r}"]


def to_float(text: str):
    try:
        return float(text)
    except ValueError:
        return None


def compare_csv(expected_text: str, actual_text: str) -> list[str]:
    expected_rows = list(csv.reader(expected_text.splitlines()))
    actual_rows = list(csv.reader(actual_text.splitlines()))
    if len(expected_rows) != len(actual_rows):
        return [f"rows {len(expected_rows)} != {len(actual_rows)}"]
    problems = []
    for r, (erow, arow) in enumerate(zip(expected_rows, actual_rows), start=1):
        if len(erow) != len(arow):
            problems.append(f"row {r}: columns {len(erow)} != {len(arow)}")
            continue
        for c, (e, a) in enumerate(zip(erow, arow), start=1):
            if e == a:
                continue
            ev, av = to_float(e), to_float(a)
            if r > 1 and ev is not None and av is not None and numbers_match(ev, av):
                continue
            problems.append(f"row {r}, column {c}: {e!r} != {a!r}")
    return problems


def compare_file(name: str, expected_text: str, actual_text: str) -> list[str]:
    if name.endswith(".json"):
        return compare_json(json.loads(expected_text), json.loads(actual_text))
    if name.endswith(".csv"):
        return compare_csv(expected_text, actual_text)
    return [] if expected_text == actual_text else ["text differs"]


def main() -> int:
    sys.path.insert(0, str(CODE))
    suite = unittest.defaultTestLoader.discover(str(CODE), pattern="test_model.py")
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful() or outcome.skipped:
        return 1

    saved_names = sorted(p.name for p in (ROOT / "results").iterdir())
    if saved_names != sorted(EXPECTED_RESULT_FILES):
        raise RuntimeError(
            f"results/ holds {saved_names}, but this script compares {sorted(EXPECTED_RESULT_FILES)}")

    matched = []
    with tempfile.TemporaryDirectory(prefix="disc-model-") as directory:
        destination = Path(directory)
        try:
            subprocess.run(
                [sys.executable, str(CODE / "model.py"), "--config",
                 str(CODE / "scenarios.json"), "--out", str(destination)],
                check=True, capture_output=True, text=True,
            )
        except subprocess.CalledProcessError as error:
            print(error.stderr, file=sys.stderr)
            raise
        experiments = importlib.import_module("experiments")
        experiments.run(out=destination)
        for name in EXPECTED_RESULT_FILES:
            # CSV writers can use OS-specific line endings; compare decoded text.
            expected = (ROOT / "results" / name).read_text(encoding="utf-8")
            actual = (destination / name).read_text(encoding="utf-8")
            problems = compare_file(name, expected, actual)
            if problems:
                shown = "; ".join(problems[:5])
                raise RuntimeError(
                    f"Saved result differs: {name} ({len(problems)} places). {shown}")
            matched.append(name)

    notebook = json.loads((ROOT / "analysis.ipynb").read_text(encoding="utf-8"))
    code_cells = 0
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]), feature_version=SYNTAX_TARGET)
            code_cells += 1
    for path in CODE.glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), feature_version=SYNTAX_TARGET)
    print(json.dumps({
        "python": ".".join(str(n) for n in sys.version_info[:3]),
        "model_tests_passed": outcome.testsRun,
        "skipped": len(outcome.skipped),
        "saved_result_files_matched": matched,
        "number_comparison": f"math.isclose(rel_tol={REL_TOL}, abs_tol={ABS_TOL}); strings exact",
        "notebook_code_cells_syntax_checked": code_cells,
        "syntax_target": ".".join(str(n) for n in SYNTAX_TARGET),
        "note": "Syntax check is not execution on that Python version.",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
