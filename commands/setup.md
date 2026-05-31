---
description: 首次安装：建立 Python venv、安装依赖、初始化 SQLite + CSBMK 数据
allowed-tools: Bash, Read
---

执行以下步骤，按顺序：

1. 检测 Plugin 安装路径并定义数据目录（兼容 marketplace 与旧扁平布局）：
   ```bash
   # 1) 优先用 Claude Code 注入的规范变量
   PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT:-}"
   # 2) 回退：marketplace 布局 cache/<market>/cost-estimation/<version>，按版本号取最新
   if [ -z "$PLUGIN_DIR" ] || [ ! -d "$PLUGIN_DIR/server" ]; then
     PLUGIN_DIR=$(ls -d "$HOME"/.claude/plugins/cache/*/cost-estimation/*/ 2>/dev/null | sort -V | tail -1)
     PLUGIN_DIR="${PLUGIN_DIR%/}"
   fi
   # 3) 回退：旧扁平布局
   [ -d "$PLUGIN_DIR/server" ] || PLUGIN_DIR="$HOME/.claude/plugins/cache/cost-estimation"
   [ -d "$PLUGIN_DIR/server" ] || PLUGIN_DIR="$HOME/.claude/plugins/data/cost-estimation"
   [ -d "$PLUGIN_DIR/server" ] || { echo "✗ 未找到插件安装目录（缺少 server/）"; exit 1; }
   DATA_DIR="$HOME/.claude/projects/cost-estimation"
   echo "PLUGIN_DIR=$PLUGIN_DIR"
   echo "DATA_DIR=$DATA_DIR"
   ```

2. 在 `$PLUGIN_DIR/server` 下创建 venv 并跑 preflight（Python 版本 + libmagic + pip 镜像）：
   ```bash
   cd "$PLUGIN_DIR/server"
   # 探测 ≥3.11 的解释器（系统默认 python3 可能是 3.9，会令 preflight 直接失败）
   PYBIN=""
   for cand in python3.13 python3.12 python3.11 python3; do
     command -v "$cand" >/dev/null 2>&1 || continue
     v=$("$cand" -c 'import sys;print(sys.version_info[0]*100+sys.version_info[1])' 2>/dev/null)
     if [ -n "$v" ] && [ "$v" -ge 311 ]; then PYBIN="$cand"; break; fi
   done
   [ -z "$PYBIN" ] && { echo "✗ 未找到 Python ≥ 3.11，请先安装（如 brew install python@3.11）后重试"; exit 1; }
   echo "使用解释器：$PYBIN ($("$PYBIN" --version 2>&1))"
   if [ ! -d ".venv" ]; then
     "$PYBIN" -m venv .venv
   fi
   source .venv/bin/activate
   pip install --upgrade pip click --quiet
   python -m app.preflight \
     || { echo "✗ Preflight 失败，请按上方提示安装缺失依赖后重试"; exit 1; }
   ```

3. 创建数据目录，并清理失效的运行态残留（仅当后端进程已死）：
   ```bash
   mkdir -p "$DATA_DIR"/{db,uploads,exports}
   if [ -f "$DATA_DIR/.pid" ]; then
     OLD_PID=$(cat "$DATA_DIR/.pid" 2>/dev/null)
     if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
       echo "ℹ 后端仍在运行 (PID=$OLD_PID)，保留 .pid/.token/.port；如需重装请先 /cost-estimation:cost-stop"
     else
       rm -f "$DATA_DIR/.pid" "$DATA_DIR/.token" "$DATA_DIR/.port"
       echo "✓ 已清理失效的 .pid/.token/.port 残留"
     fi
   fi
   ```

4. 安装后端依赖（preflight 通过后执行）：
   ```bash
   pip install -r requirements.txt --quiet \
     -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

5. 初始化 SQLite + 装载 SSM-BK-202509 基准数据（v2.9 起取代 CSBMK®-202510）：
   ```bash
   python -m app.bootstrap \
     --db "$DATA_DIR/db/cost.sqlite" \
     --seed "$PLUGIN_DIR/server/app/data/ssm_bk_202509.json"
   ```

6. 检查并按需构建前端（仓库通常已携带 `web/dist/`，此为 fallback）：
   ```bash
   if [ ! -f "$PLUGIN_DIR/web/dist/index.html" ]; then
     echo "⚠ 未找到 web/dist/，尝试本地构建..."
     if command -v pnpm >/dev/null 2>&1; then
       cd "$PLUGIN_DIR/web" && pnpm install --silent && pnpm build \
         || { echo "✗ 前端构建失败"; exit 1; }
     elif command -v npm >/dev/null 2>&1; then
       cd "$PLUGIN_DIR/web" && npm install --silent && npm run build \
         || { echo "✗ 前端构建失败"; exit 1; }
     else
       echo "✗ 缺少 pnpm/npm，无法构建前端。请安装 Node.js 20+ 与 pnpm 9 后重试。"
       exit 1
     fi
   fi
   ```

7. 报告："✓ 安装完成。运行 /cost 即可启动 Web 界面"
