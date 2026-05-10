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

2. 检测 Python 3.11+ 与 libmagic（preflight）：
   ```bash
   python3 --version | grep -E "Python 3\.(11|12|13)" \
     || { echo "✗ 需要 Python 3.11 及以上"; exit 1; }
   python3 -c "import ctypes.util; assert ctypes.util.find_library('magic'), '请先安装 libmagic：macOS 用 brew install libmagic / Ubuntu 用 apt install libmagic1'" \
     || exit 1
   ```

3. 创建数据目录：
   ```bash
   mkdir -p "$DATA_DIR"/{db,uploads,exports}
   ```

4. 在 `$PLUGIN_DIR/server` 下创建 venv 并安装依赖：
   ```bash
   cd "$PLUGIN_DIR/server"
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip --quiet
   pip install -r requirements.txt --quiet \
     -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

5. 初始化 SQLite + 装载 CSBMK®-202510 默认参数：
   ```bash
   python -m app.bootstrap \
     --db "$DATA_DIR/db/cost.sqlite" \
     --seed "$PLUGIN_DIR/server/app/data/csbmk_202510.json"
   ```

6. 报告："✓ 安装完成。运行 /cost 即可启动 Web 界面"
