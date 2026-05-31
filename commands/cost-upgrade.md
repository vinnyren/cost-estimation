---
description: 升级既有安装：备份 + alembic 迁移 + 基准重灯(SSM-BK-202509) + 刷新 venv/前端
allowed-tools: Bash, Read
---

执行以下步骤，按顺序：

1. 路径检测 + 数据目录（与 setup 一致，兼容 marketplace 与旧扁平布局）：
   ```bash
   PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT:-}"
   if [ -z "$PLUGIN_DIR" ] || [ ! -d "$PLUGIN_DIR/server" ]; then
     PLUGIN_DIR=$(ls -d "$HOME"/.claude/plugins/cache/*/cost-estimation/*/ 2>/dev/null | sort -V | tail -1)
     PLUGIN_DIR="${PLUGIN_DIR%/}"
   fi
   [ -d "$PLUGIN_DIR/server" ] || PLUGIN_DIR="$HOME/.claude/plugins/cache/cost-estimation"
   [ -d "$PLUGIN_DIR/server" ] || PLUGIN_DIR="$HOME/.claude/plugins/data/cost-estimation"
   [ -d "$PLUGIN_DIR/server" ] || { echo "✗ 未找到插件安装目录"; exit 1; }
   DATA_DIR="$HOME/.claude/projects/cost-estimation"
   DB="$DATA_DIR/db/cost.sqlite"
   [ -f "$DB" ] || { echo "✗ 未找到数据库（升级≠首装），请先 /cost-estimation:setup"; exit 1; }
   ```

2. 停止运行中的后端（升级不可对活库动手）：
   ```bash
   if [ -f "$DATA_DIR/.pid" ]; then
     PID=$(cat "$DATA_DIR/.pid")
     if kill -0 "$PID" 2>/dev/null; then
       kill "$PID"; for i in 1 2 3 4 5; do kill -0 "$PID" 2>/dev/null || break; sleep 1; done
       kill -0 "$PID" 2>/dev/null && kill -9 "$PID"
       echo "✓ 已停止后端 PID=$PID"
     fi
   fi
   rm -f "$DATA_DIR/.pid" "$DATA_DIR/.token" "$DATA_DIR/.port"
   ```

3. 确保 venv(≥3.11) 并刷新依赖：
   ```bash
   cd "$PLUGIN_DIR/server"
   PYBIN=""
   for cand in python3.13 python3.12 python3.11 python3; do
     command -v "$cand" >/dev/null 2>&1 || continue
     v=$("$cand" -c 'import sys;print(sys.version_info[0]*100+sys.version_info[1])' 2>/dev/null)
     if [ -n "$v" ] && [ "$v" -ge 311 ]; then PYBIN="$cand"; break; fi
   done
   [ -z "$PYBIN" ] && { echo "✗ 未找到 Python ≥ 3.11"; exit 1; }
   [ -d ".venv" ] || "$PYBIN" -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt --quiet -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

4. 执行升级编排（备份 + schema 修复 + 基准重灯）：
   ```bash
   TS=$(date +%Y%m%dT%H%M%S)
   python -m app.upgrade \
     --db "$DB" \
     --seed "$PLUGIN_DIR/server/app/data/ssm_bk_202509.json" \
     --ts "$TS"
   ```

5. 前端 fallback（仓库通常已携带 web/dist/）：
   ```bash
   if [ ! -f "$PLUGIN_DIR/web/dist/index.html" ]; then
     echo "⚠ 未找到 web/dist/，尝试本地构建..."
     if command -v pnpm >/dev/null 2>&1; then
       cd "$PLUGIN_DIR/web" && pnpm install --silent && pnpm build || { echo "✗ 前端构建失败"; exit 1; }
     elif command -v npm >/dev/null 2>&1; then
       cd "$PLUGIN_DIR/web" && npm install --silent && npm run build || { echo "✗ 前端构建失败"; exit 1; }
     else
       echo "✗ 缺少 pnpm/npm，无法构建前端。"; exit 1
     fi
   fi
   ```

6. 报告："✓ 升级完成。历史项目需重新触发一次计算才反映新基准口径。运行 /cost 启动。"
