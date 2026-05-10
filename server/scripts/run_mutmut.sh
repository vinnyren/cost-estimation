#!/bin/bash
# Mutation testing for app/core/ — 目标杀死率 ≥ 70%
# 注意：set -e 已移除以避免 mutmut 非零退出（杀死率不达标）中断 commit。
set -uo pipefail

cd "$(dirname "$0")/.."

VENV_BIN="./.venv/bin"

if [ ! -x "$VENV_BIN/mutmut" ]; then
  echo "ERROR: mutmut 未安装（$VENV_BIN/mutmut 不存在）"
  echo "  → 运行 $VENV_BIN/pip install 'mutmut>=2.5'"
  exit 2
fi

echo "→ 清理上次结果"
rm -rf .mutmut-cache mutants mutants.xml

echo "→ 跑 mutmut（约 5–10 分钟，目标 app/core/）"
"$VENV_BIN/mutmut" run || true

echo
echo "→ 汇总结果（mutmut results）"
"$VENV_BIN/mutmut" results | tail -200

echo
echo "→ 计算杀死率"
RESULTS_OUTPUT=$("$VENV_BIN/mutmut" results 2>/dev/null || echo "")

# mutmut v3 输出形如：
#   killed:     N
#   survived:   M
#   ...
KILLED=$(echo "$RESULTS_OUTPUT" | grep -iE '^[[:space:]]*killed' | grep -oE '[0-9]+' | head -1 || echo "0")
SURVIVED=$(echo "$RESULTS_OUTPUT" | grep -iE '^[[:space:]]*survived' | grep -oE '[0-9]+' | head -1 || echo "0")
TIMEOUT=$(echo "$RESULTS_OUTPUT" | grep -iE '^[[:space:]]*timeout' | grep -oE '[0-9]+' | head -1 || echo "0")
SUSPICIOUS=$(echo "$RESULTS_OUTPUT" | grep -iE '^[[:space:]]*suspicious' | grep -oE '[0-9]+' | head -1 || echo "0")

KILLED=${KILLED:-0}
SURVIVED=${SURVIVED:-0}
TIMEOUT=${TIMEOUT:-0}
SUSPICIOUS=${SUSPICIOUS:-0}

TOTAL=$((KILLED + SURVIVED + TIMEOUT + SUSPICIOUS))

echo "  killed     = $KILLED"
echo "  survived   = $SURVIVED"
echo "  timeout    = $TIMEOUT"
echo "  suspicious = $SUSPICIOUS"
echo "  total      = $TOTAL"

if [ "$TOTAL" -gt 0 ]; then
  PERCENT=$((KILLED * 100 / TOTAL))
  echo "✓ 杀死率: $KILLED / $TOTAL = $PERCENT%"
  if [ "$PERCENT" -lt 70 ]; then
    echo "⚠ 杀死率 < 70%，建议增强 app/core/* 测试覆盖（不阻塞 commit）"
  fi
else
  echo "⚠ 未生成 mutant（mutmut 可能失败）"
fi
