#!/usr/bin/env python3
"""Compare current coverage against baseline. Exit 1 if regression > tolerance.

Used by scripts/check-coverage.sh. Reads coverage-baseline.json from repo root.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: _compare-coverage.py <backend_pct> <frontend_pct>",
            file=sys.stderr,
        )
        return 2
    try:
        current_backend = float(sys.argv[1])
        current_frontend = float(sys.argv[2])
    except ValueError:
        print("Coverage values must be numeric", file=sys.stderr)
        return 2

    repo_root = Path(__file__).resolve().parent.parent
    baseline_path = repo_root / "coverage-baseline.json"
    if not baseline_path.exists():
        print(
            f"ERROR: {baseline_path} not found. "
            "Run scripts/update-coverage-baseline.sh once to establish baseline.",
            file=sys.stderr,
        )
        return 1
    baseline = json.loads(baseline_path.read_text())
    tolerance = float(baseline.get("tolerance_pct", 0.5))

    issues: list[str] = []
    improvements: list[str] = []

    for label, key, current in [
        ("Backend", "backend", current_backend),
        ("Frontend", "frontend", current_frontend),
    ]:
        baseline_pct = float(baseline[key]["line_coverage_pct"])
        delta = current - baseline_pct
        if delta < -tolerance:
            issues.append(
                f"  ✗ {label}: {current:.2f}% (baseline {baseline_pct:.2f}%, "
                f"delta {delta:+.2f}, tolerance {tolerance})"
            )
        elif delta > tolerance:
            improvements.append(
                f"  ↑ {label}: {current:.2f}% (baseline {baseline_pct:.2f}%, "
                f"delta {delta:+.2f})"
            )
        else:
            print(f"  ✓ {label}: {current:.2f}% (baseline {baseline_pct:.2f}%)")

    if improvements:
        print("\n覆盖率上升：")
        for line in improvements:
            print(line)
        print("\n建议：scripts/update-coverage-baseline.sh 锁定新 baseline。")

    if issues:
        print("\n✗ 覆盖率退化超过 tolerance：", file=sys.stderr)
        for line in issues:
            print(line, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
