#!/usr/bin/env bash
# 验证当前 coverage 不退化于 coverage-baseline.json。
# 用法：scripts/check-coverage.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "→ 跑 backend pytest --cov ..."
(cd server && .venv/bin/pytest --cov=app --cov-report=json:coverage.json -q > /tmp/cov-backend.log 2>&1) || {
    echo "✗ Backend tests 失败 — 详见 /tmp/cov-backend.log" >&2
    exit 1
}
BACKEND_PCT=$(python3 -c "import json; d=json.load(open('server/coverage.json')); print(round(d['totals']['percent_covered'], 2))")

echo "→ 跑 frontend vitest --coverage ..."
(cd web && pnpm test:coverage --reporter=dot > /tmp/cov-frontend.log 2>&1) || {
    echo "✗ Frontend tests 失败 — 详见 /tmp/cov-frontend.log" >&2
    exit 1
}
FRONTEND_PCT=$(python3 -c "import json; d=json.load(open('web/coverage/coverage-summary.json')); print(d['total']['lines']['pct'])")

echo ""
echo "→ 比对 coverage-baseline.json ..."
python3 scripts/_compare-coverage.py "$BACKEND_PCT" "$FRONTEND_PCT"
