#!/usr/bin/env bash
# 重写 coverage-baseline.json 为当前覆盖率。
# 用户手动调用 — 在覆盖率上升后锁定新 baseline。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "→ 跑 backend pytest --cov ..."
(cd server && .venv/bin/pytest --cov=app --cov-report=json:coverage.json -q > /dev/null)
BACKEND_PCT=$(python3 -c "import json; d=json.load(open('server/coverage.json')); print(round(d['totals']['percent_covered'], 2))")

echo "→ 跑 frontend vitest --coverage ..."
(cd web && pnpm test:coverage --reporter=dot > /dev/null)
FRONTEND_PCT=$(python3 -c "import json; d=json.load(open('web/coverage/coverage-summary.json')); print(d['total']['lines']['pct'])")

COMMIT=$(git rev-parse --short HEAD)
TODAY=$(date +%Y-%m-%d)
TOLERANCE=$(python3 -c "import json; d=json.load(open('coverage-baseline.json')); print(d.get('tolerance_pct', 0.5))")

export BACKEND_PCT FRONTEND_PCT COMMIT TODAY TOLERANCE

python3 - <<'PYEOF'
import json
import os

backend_pct = float(os.environ["BACKEND_PCT"])
frontend_pct = float(os.environ["FRONTEND_PCT"])
commit = os.environ["COMMIT"]
today = os.environ["TODAY"]
tolerance = float(os.environ["TOLERANCE"])

baseline = {
    "$schema": "本地 baseline — scripts/check-coverage.sh 用来防止 PR 让覆盖率退化超过 tolerance",
    "captured_at": today,
    "captured_at_commit": commit,
    "tolerance_pct": tolerance,
    "backend": {
        "line_coverage_pct": backend_pct,
        "source": "server/coverage.json -> totals.percent_covered",
    },
    "frontend": {
        "line_coverage_pct": frontend_pct,
        "source": "web/coverage/coverage-summary.json -> total.lines.pct",
    },
}
with open("coverage-baseline.json", "w") as f:
    json.dump(baseline, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"✓ baseline 已更新：backend {backend_pct}% / frontend {frontend_pct}% (commit {commit})")
PYEOF
