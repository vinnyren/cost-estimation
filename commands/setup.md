---
description: 首次安装：建立 Python venv、安装依赖、初始化 SQLite + CSBMK 数据
allowed-tools: Bash, Read
---

执行以下步骤，按顺序：

1. 检测 Plugin 安装路径并定义数据目录：
   ```bash
   PLUGIN_DIR="$HOME/.claude/plugins/cache/cost-estimation"
   if [ ! -d "$PLUGIN_DIR" ]; then
     PLUGIN_DIR="$HOME/.claude/plugins/data/cost-estimation"
   fi
   DATA_DIR="$HOME/.claude/projects/cost-estimation"
   echo "PLUGIN_DIR=$PLUGIN_DIR"
   echo "DATA_DIR=$DATA_DIR"
   ```

2. 在 `$PLUGIN_DIR/server` 下创建 venv 并跑 preflight（Python 版本 + libmagic + pip 镜像）：
   ```bash
   cd "$PLUGIN_DIR/server"
   if [ ! -d ".venv" ]; then
     python3 -m venv .venv
   fi
   source .venv/bin/activate
   pip install --upgrade pip click --quiet
   python -m app.preflight \
     || { echo "✗ Preflight 失败，请按上方提示安装缺失依赖后重试"; exit 1; }
   ```

3. 创建数据目录：
   ```bash
   mkdir -p "$DATA_DIR"/{db,uploads,exports}
   ```

4. 安装后端依赖（preflight 通过后执行）：
   ```bash
   pip install -r requirements.txt --quiet \
     -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

5. 初始化 SQLite + 装载 CSBMK®-202510 默认参数：
   ```bash
   python -m app.bootstrap \
     --db "$DATA_DIR/db/cost.sqlite" \
     --seed "$PLUGIN_DIR/server/app/data/csbmk_202510.json"
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
