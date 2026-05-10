# Plan 4 — Plugin 打包 + 端到端测试 + 文档 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Plan 1+2+3 的产物打包为 Claude Code Plugin，提供 `/plugin install cost-estimation` 一键安装路径，配套 setup/cost/cost-stop 三条 slash 命令、SKILL.md（含 NESMA 规则）、Playwright E2E 测试、mutation testing 报告、完整用户与开发者文档。

**Architecture:** 在仓库根新增 `.claude-plugin/` 元信息目录（marketplace.json + plugin.json），`commands/` 三条命令文件，`SKILL.md` 与 `reference/nesma-rules.md` 让 Claude 能 AI 提取 FP 初稿；新增 `server/app/bootstrap.py` CLI 完成首次 SQLite 初始化与 CSBMK seed；新增 `tests/e2e/` 用 Playwright 覆盖 forward + reverse 完整流程；用 `mutmut` 对 `server/app/core/*` 做变异测试；最后写 README + user-guide + dev-guide 三份文档。

**Tech Stack:** Python 3.11 / Click（CLI）/ Playwright 1.45（E2E）/ mutmut 2.5 / Markdown 文档 / Claude Code Plugin manifest 1.0 spec。

---

## 任务总览

| # | Task | 主要产出 |
|---|---|---|
| T1 | Plugin 元信息 + 仓库结构 | `.claude-plugin/marketplace.json`、`plugin.json`、目录骨架 |
| T2 | bootstrap.py CLI + commands/setup.md | 首次安装命令 + DB 初始化工具 |
| T3 | commands/cost.md + commands/cost-stop.md | 启动/停止后端 + token 协议 |
| T4 | SKILL.md + reference/nesma-rules.md | AI 提取 FP 的触发与规则 |
| T5 | 安装 preflight 脚本 | 检测 Python/libmagic/pip 镜像 |
| T6 | Playwright E2E（forward + reverse） | tests/e2e/* + CI 配置（仅本地说明） |
| T7 | mutation testing（mutmut on core/） | mutation 报告 + 杀死率 ≥ 70% |
| T8 | 用户与开发者文档 | README.md + docs/user-guide.md + docs/dev-guide.md |

每个 Task 遵循 TDD：先写测试（如适用）→ 实现 → 测试通过 → commit。文档型 Task（T1/T8）以"smoke 校验脚本"代替单测。

---

## Task 1: Plugin 元信息 + 仓库结构

**Files:**
- Create: `.claude-plugin/marketplace.json`
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/.gitkeep`
- Create: `commands/.gitkeep`
- Create: `reference/.gitkeep`
- Create: `tests/e2e/.gitkeep`
- Modify: `.gitignore`（追加 `playwright-report/`、`test-results/`、`.mutmut-cache/`、`mutants/`）
- Test: `tests/plugin_manifest_test.py`

- [ ] **Step 1: 写 manifest 校验测试**

```python
# tests/plugin_manifest_test.py
"""校验 .claude-plugin/*.json 是否符合 Claude Code plugin 规范。"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict:
    return json.loads((REPO / path).read_text(encoding="utf-8"))


def test_marketplace_json_required_fields():
    m = _load(".claude-plugin/marketplace.json")
    assert m["name"] == "cost-estimation-marketplace"
    assert "owner" in m and m["owner"]["name"]
    assert "metadata" in m and m["metadata"]["version"] == "1.0.0"
    assert isinstance(m["plugins"], list) and len(m["plugins"]) >= 1
    plugin = m["plugins"][0]
    assert plugin["name"] == "cost-estimation"
    assert plugin["source"]["source"] == "url"
    assert plugin["source"]["url"].startswith("https://")
    assert plugin["strict"] is True


def test_plugin_json_lists_three_commands():
    p = _load(".claude-plugin/plugin.json")
    assert p["name"] == "cost-estimation"
    assert p["version"] == "1.0.0"
    cmd_paths = p["commands"]
    assert "./commands/setup.md" in cmd_paths
    assert "./commands/cost.md" in cmd_paths
    assert "./commands/cost-stop.md" in cmd_paths
    assert p["license"] == "MIT"
    assert "cost-estimation" in p["keywords"]
    assert "GB-T-36964" in p["keywords"]


def test_directory_skeleton_exists():
    """T1 后必备目录骨架。"""
    for d in (".claude-plugin", "commands", "reference", "tests/e2e"):
        assert (REPO / d).is_dir(), f"missing dir: {d}"
```

- [ ] **Step 2: 跑测试，确认失败**

```bash
cd /Users/renzhongyuan/WorkData/项目/2026/造价应用
python3 -m pytest tests/plugin_manifest_test.py -v
# 期望: 全部 fail（文件不存在）
```

- [ ] **Step 3: 创建 .claude-plugin/marketplace.json**

```json
{
  "name": "cost-estimation-marketplace",
  "owner": {
    "name": "Cost Estimation Team",
    "email": "noreply@example.com"
  },
  "metadata": {
    "description": "软件造价评估工具集（基于 GB/T 36964 / T/CCUA 005-2024 / CSBMK®-202510）",
    "version": "1.0.0"
  },
  "plugins": [
    {
      "name": "cost-estimation",
      "source": {
        "source": "url",
        "url": "https://github.com/your-org/cost-estimation.git"
      },
      "description": "基于 GB/T 36964 / T/CCUA 005-2024 / CSBMK®-202510 的软件造价制作系统",
      "version": "1.0.0",
      "strict": true
    }
  ]
}
```

- [ ] **Step 4: 创建 .claude-plugin/plugin.json**

```json
{
  "name": "cost-estimation",
  "description": "软件造价评估 · NESMA 估算 · 双向（FP↔成本）",
  "version": "1.0.0",
  "author": {
    "name": "Cost Estimation Team",
    "url": "https://github.com/your-org/cost-estimation"
  },
  "commands": [
    "./commands/setup.md",
    "./commands/cost.md",
    "./commands/cost-stop.md"
  ],
  "license": "MIT",
  "keywords": [
    "cost-estimation",
    "function-points",
    "NESMA",
    "GB-T-36964",
    "CSBMK"
  ]
}
```

- [ ] **Step 5: 创建占位文件**

```bash
touch .claude-plugin/.gitkeep commands/.gitkeep reference/.gitkeep tests/e2e/.gitkeep
```

- [ ] **Step 6: 修改 .gitignore 追加 Playwright/mutmut 工件**

在顶层 `.gitignore` 末尾追加：

```
# Playwright
playwright-report/
test-results/

# mutation testing
.mutmut-cache/
mutants/
```

- [ ] **Step 7: 跑测试验证通过**

```bash
python3 -m pytest tests/plugin_manifest_test.py -v
# 期望: 3 个用例 PASS
```

- [ ] **Step 8: Commit**

```bash
git add .claude-plugin/ commands/.gitkeep reference/.gitkeep tests/e2e/.gitkeep tests/plugin_manifest_test.py .gitignore
git commit -m "feat(plugin): add .claude-plugin manifest + repo skeleton"
```

---

## Task 2: bootstrap.py CLI + commands/setup.md

**Files:**
- Create: `server/app/bootstrap.py`
- Create: `commands/setup.md`
- Modify: `server/pyproject.toml`（追加 `click>=8.1` 到 dependencies）
- Modify: `server/requirements.txt`（同上）
- Test: `server/tests/integration/test_bootstrap.py`

- [ ] **Step 1: 写 bootstrap 集成测试**

```python
# server/tests/integration/test_bootstrap.py
"""集成：app.bootstrap 应能初始化 SQLite + 装载 CSBMK seed。"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture
def seed_file(tmp_path: Path) -> Path:
    seed = tmp_path / "csbmk-test.json"
    seed.write_text(json.dumps({
        "version": "TEST-202510",
        "effective_date": "2025-10-01",
        "productivity": {
            "dev": {"全行业": {"P10": 2.0, "P50": 6.7, "P90": 17.0}},
            "ops": {"全行业": {"P10": 0.2, "P50": 0.7, "P90": 2.0}},
        },
        "city_rate": {"北京": {"dev": 32198, "ops": 26335, "class": "A"}},
        "cf": {"bidding": 1.21},
        "factors_dev": {"app_type": {"业务处理": 1.0}},
        "factors_ops": {"update_freq": {"monthly": 1.0}},
        "hours_per_pm": 174,
        "ops_cost_ratio": {"P50": 0.0902},
    }), encoding="utf-8")
    return seed


def test_bootstrap_creates_schema_and_seeds(tmp_path: Path, seed_file: Path):
    from app.bootstrap import cli

    db_path = tmp_path / "cost.sqlite"
    runner = CliRunner()
    result = runner.invoke(cli, ["--db", str(db_path), "--seed", str(seed_file)])

    assert result.exit_code == 0, result.output
    assert "✓" in result.output
    assert db_path.exists()

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    tables = {row[0] for row in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    # 至少应含 plan 1 创建的核心表
    assert "projects" in tables
    assert "params_global" in tables
    cur.execute("SELECT json_extract(value, '$.version') FROM params_global LIMIT 1")
    version = cur.fetchone()[0]
    assert version == "TEST-202510"
    con.close()


def test_bootstrap_idempotent(tmp_path: Path, seed_file: Path):
    """二次运行不应破坏已有数据。"""
    from app.bootstrap import cli

    db_path = tmp_path / "cost.sqlite"
    runner = CliRunner()

    r1 = runner.invoke(cli, ["--db", str(db_path), "--seed", str(seed_file)])
    assert r1.exit_code == 0

    # 创建一个项目
    con = sqlite3.connect(str(db_path))
    con.execute(
        "INSERT INTO projects (name, mode, city, industry, stage) VALUES (?, ?, ?, ?, ?)",
        ("user-data", "forward", "北京", "全行业", "bidding"),
    )
    con.commit()
    con.close()

    r2 = runner.invoke(cli, ["--db", str(db_path), "--seed", str(seed_file)])
    assert r2.exit_code == 0
    assert "已存在" in r2.output or "skip" in r2.output.lower()

    con = sqlite3.connect(str(db_path))
    cur = con.execute("SELECT count(*) FROM projects WHERE name=?", ("user-data",))
    assert cur.fetchone()[0] == 1
    con.close()


def test_bootstrap_missing_seed_fails(tmp_path: Path):
    from app.bootstrap import cli

    db_path = tmp_path / "cost.sqlite"
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--db", str(db_path), "--seed", str(tmp_path / "nonexistent.json")]
    )
    assert result.exit_code != 0
    assert "seed" in result.output.lower() or "not found" in result.output.lower()
```

- [ ] **Step 2: 跑测试验证失败**

```bash
cd server && /Users/renzhongyuan/WorkData/项目/2026/造价应用/server/.venv/bin/pytest tests/integration/test_bootstrap.py -v
# 期望: ImportError(app.bootstrap) → 失败
```

- [ ] **Step 3: 在 server/pyproject.toml dependencies 追加 click>=8.1**

```toml
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "python-multipart>=0.0.9",
    "pdfplumber>=0.11",
    "python-docx>=1.1",
    "openpyxl>=3.1",
    "python-magic>=0.4.27",
    "click>=8.1",
]
```

同步 server/requirements.txt 末尾追加 `click>=8.1`。

- [ ] **Step 4: 安装新依赖**

```bash
cd server && /Users/renzhongyuan/WorkData/项目/2026/造价应用/server/.venv/bin/pip install click
```

- [ ] **Step 5: 实现 server/app/bootstrap.py**

```python
"""一次性初始化脚本：建立 SQLite schema + 装载 CSBMK seed。

用法：
  python -m app.bootstrap --db ~/.claude/projects/cost-estimation/db/cost.sqlite \
                          --seed app/data/csbmk_202510.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db import Base


@click.command()
@click.option(
    "--db",
    "db_path",
    required=True,
    type=click.Path(path_type=Path),
    help="SQLite 数据库路径（必须）",
)
@click.option(
    "--seed",
    "seed_path",
    required=True,
    type=click.Path(path_type=Path, exists=False),
    help="CSBMK seed JSON 路径（必须）",
)
def cli(db_path: Path, seed_path: Path) -> None:
    """初始化数据库并装载 CSBMK 默认参数。"""
    if not seed_path.exists():
        click.echo(f"错误：seed 文件不存在: {seed_path}", err=True)
        sys.exit(2)

    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @Base.metadata.tables["params_global"].listeners.append  # type: ignore[attr-defined]
    def _noop(*_args, **_kwargs):
        pass

    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(text("PRAGMA journal_mode = WAL"))
        conn.execute(text("PRAGMA busy_timeout = 5000"))

    seed_json = json.loads(seed_path.read_text(encoding="utf-8"))

    Session = sessionmaker(bind=engine)
    with Session() as session:
        existing = session.execute(
            text("SELECT count(*) FROM params_global")
        ).scalar()
        if existing and existing > 0:
            click.echo("CSBMK 参数已存在，跳过 seed（idempotent）。")
        else:
            session.execute(
                text(
                    "INSERT INTO params_global (key, value, version, source) "
                    "VALUES (:key, :value, :version, :source)"
                ),
                {
                    "key": "csbmk",
                    "value": json.dumps(seed_json, ensure_ascii=False),
                    "version": seed_json.get("version", "unknown"),
                    "source": "csbmk_seed",
                },
            )
            session.commit()
            click.echo(
                f"✓ 已装载 CSBMK seed（版本 {seed_json.get('version', 'unknown')}）。"
            )

    click.echo(f"✓ 数据库初始化完成: {db_path}")


if __name__ == "__main__":
    cli()
```

> 注意：上述代码假设 `app.db.Base` 已在 Plan 1 落地。`params_global` 列结构（key/value/version/source）以 Plan 1 实际为准。如果列名不同，请按实际调整 INSERT 语句。

- [ ] **Step 6: 跑测试验证通过**

```bash
cd server && /Users/renzhongyuan/WorkData/项目/2026/造价应用/server/.venv/bin/pytest tests/integration/test_bootstrap.py -v
# 期望: 3 用例 PASS
```

如有列名不一致引发的 IntegrityError，回到 Step 5 修正 SQL；不要回避。

- [ ] **Step 7: 创建 commands/setup.md**

```markdown
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
```

- [ ] **Step 8: Commit**

```bash
git add server/app/bootstrap.py commands/setup.md server/pyproject.toml server/requirements.txt server/tests/integration/test_bootstrap.py
git commit -m "feat(plugin): bootstrap CLI + commands/setup.md (preflight + venv + seed)"
```

---

## Task 3: commands/cost.md + commands/cost-stop.md

**Files:**
- Create: `commands/cost.md`
- Create: `commands/cost-stop.md`
- Test: `tests/commands_smoke_test.py`

- [ ] **Step 1: 写命令 markdown 校验测试**

```python
# tests/commands_smoke_test.py
"""校验 commands/*.md 含必要 frontmatter 与关键步骤。"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (REPO / "commands" / name).read_text(encoding="utf-8")


def test_setup_command_has_frontmatter():
    body = _read("setup.md")
    assert body.startswith("---\n")
    assert "description:" in body.split("---", 2)[1]
    assert "allowed-tools:" in body.split("---", 2)[1]


def test_cost_command_starts_uvicorn_with_token():
    body = _read("cost.md")
    assert "uvicorn" in body
    assert "127.0.0.1" in body
    assert "secrets.token_urlsafe" in body or "openssl rand" in body, \
        "必须生成随机 token"
    assert "/health" in body, "必须健康检查后再开浏览器"
    assert "/?t=" in body or "?t=$TOKEN" in body, "必须把 token 拼到 URL"


def test_cost_command_handles_port_conflict():
    body = _read("cost.md")
    # 任一形式都接受
    assert "8788" in body
    assert ".port" in body or "8789" in body, \
        "必须有备用端口或 .port 写入"


def test_cost_stop_command_kills_pid():
    body = _read("cost-stop.md")
    assert "kill" in body
    assert ".pid" in body or "pgrep" in body or "lsof" in body
```

- [ ] **Step 2: 跑测试验证失败**

```bash
python3 -m pytest tests/commands_smoke_test.py -v
# 期望: 全部 fail
```

- [ ] **Step 3: 创建 commands/cost.md**

```markdown
---
description: 启动造价评估 Web 服务（生成随机 token，写入 .token / .port / .pid，浏览器打开）
allowed-tools: Bash
---

启动后端：

1. 定义路径：
   ```bash
   PLUGIN_DIR="$HOME/.claude/plugins/cache/cost-estimation"
   [ -d "$PLUGIN_DIR" ] || PLUGIN_DIR="$HOME/.claude/plugins/data/cost-estimation"
   DATA_DIR="$HOME/.claude/projects/cost-estimation"
   mkdir -p "$DATA_DIR"
   ```

2. 检测 8788 端口是否占用，若占用则尝试 8789–8800：
   ```bash
   PORT=""
   for p in 8788 8789 8790 8791 8792 8793 8794 8795 8796 8797 8798 8799 8800; do
     if ! lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1; then
       PORT=$p
       break
     fi
   done
   [ -z "$PORT" ] && { echo "✗ 8788–8800 端口全部占用"; exit 1; }
   echo "$PORT" > "$DATA_DIR/.port"
   ```

3. 生成一次性 token：
   ```bash
   TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
   echo "$TOKEN" > "$DATA_DIR/.token"
   chmod 600 "$DATA_DIR/.token"
   ```

4. 启动 uvicorn（后台），把 PID 写入 .pid：
   ```bash
   cd "$PLUGIN_DIR/server"
   AUTH_TOKEN="$TOKEN" \
   COST_DATABASE_URL="sqlite:///$DATA_DIR/db/cost.sqlite" \
   COST_WEB_DIST_DIR="$PLUGIN_DIR/web/dist" \
   COST_UPLOAD_DIR="$DATA_DIR/uploads" \
   COST_EXPORT_DIR="$DATA_DIR/exports" \
   nohup ".venv/bin/uvicorn" \
     app.main:app --host 127.0.0.1 --port "$PORT" \
     > /tmp/cost-estimation.log 2>&1 &
   echo $! > "$DATA_DIR/.pid"
   ```

5. 轮询 `http://127.0.0.1:$PORT/health` 直到就绪（最多 10 秒）：
   ```bash
   for i in $(seq 1 20); do
     if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
       break
     fi
     sleep 0.5
   done
   ```

6. 在默认浏览器打开（携带 token）：
   ```bash
   URL="http://127.0.0.1:$PORT/?t=$TOKEN"
   case "$(uname -s)" in
     Darwin) open "$URL" ;;
     Linux)  xdg-open "$URL" ;;
     MINGW*|MSYS*|CYGWIN*) start "$URL" ;;
     *) echo "请手动打开：$URL" ;;
   esac
   echo "✓ 已启动: $URL"
   echo "  日志: /tmp/cost-estimation.log"
   echo "  停止: 运行 /cost-estimation:cost-stop"
   ```
```

- [ ] **Step 4: 创建 commands/cost-stop.md**

```markdown
---
description: 停止造价评估后端服务并清理 .pid / .token / .port
allowed-tools: Bash
---

1. 读取 PID 并 kill：
   ```bash
   DATA_DIR="$HOME/.claude/projects/cost-estimation"
   if [ -f "$DATA_DIR/.pid" ]; then
     PID=$(cat "$DATA_DIR/.pid")
     if kill -0 "$PID" 2>/dev/null; then
       kill "$PID" && echo "✓ 已停止 PID=$PID"
       sleep 1
       kill -0 "$PID" 2>/dev/null && kill -9 "$PID"
     else
       echo "PID=$PID 已不存在"
     fi
     rm -f "$DATA_DIR/.pid"
   else
     echo "未找到 .pid，尝试用 lsof 兜底..."
     PORT_FILE="$DATA_DIR/.port"
     if [ -f "$PORT_FILE" ]; then
       PORT=$(cat "$PORT_FILE")
       LISTENERS=$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)
       [ -n "$LISTENERS" ] && kill $LISTENERS && echo "✓ 已停止端口 $PORT 上的进程"
     fi
   fi
   ```

2. 清理一次性 token：
   ```bash
   rm -f "$DATA_DIR/.token" "$DATA_DIR/.port"
   echo "✓ 已清理 .token / .port"
   ```
```

- [ ] **Step 5: 跑测试验证通过**

```bash
python3 -m pytest tests/commands_smoke_test.py -v
# 期望: 4 用例 PASS
```

- [ ] **Step 6: Commit**

```bash
git add commands/cost.md commands/cost-stop.md tests/commands_smoke_test.py
git commit -m "feat(plugin): commands/cost.md + cost-stop.md with token + port + PID lifecycle"
```

---

## Task 4: SKILL.md + reference/nesma-rules.md

**Files:**
- Create: `SKILL.md`
- Create: `reference/nesma-rules.md`
- Create: `reference/csbmk-overview.md`
- Test: `tests/skill_smoke_test.py`

- [ ] **Step 1: 写 SKILL.md 校验测试**

```python
# tests/skill_smoke_test.py
"""校验 SKILL.md 与 reference/*.md 含关键内容。"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_skill_md_frontmatter():
    body = _read("SKILL.md")
    assert body.startswith("---\n")
    head = body.split("---", 2)[1]
    assert "name: cost-estimation" in head
    assert "description:" in head


def test_skill_md_describes_trigger_phrases():
    body = _read("SKILL.md")
    for phrase in ("造价评估", "功能点", "/cost"):
        assert phrase in body


def test_skill_md_says_no_for_dangerous_actions():
    body = _read("SKILL.md")
    assert "不要" in body or "不在" in body
    # 不修改 params_global
    assert "params_global" in body
    # 不直接生成 Excel
    assert "Excel" in body


def test_nesma_rules_has_5_categories():
    body = _read("reference/nesma-rules.md")
    for cat in ("EI", "EO", "EQ", "ILF", "EIF"):
        assert cat in body, f"missing category: {cat}"


def test_csbmk_overview_documents_six_industries():
    body = _read("reference/csbmk-overview.md")
    for ind in ("电子政务", "金融", "电信", "制造", "能源", "交通"):
        assert ind in body, f"missing industry: {ind}"
```

- [ ] **Step 2: 跑测试验证失败**

```bash
python3 -m pytest tests/skill_smoke_test.py -v
```

- [ ] **Step 3: 创建 SKILL.md**

```markdown
---
name: cost-estimation
description: Use when the user wants to do software cost estimation per Chinese GB/T 36964 standards, including forward calculation (scope → cost) or reverse derivation (target cost → function points). Triggers on phrases like "造价评估", "功能点估算", "软件成本", or the slash command "/cost".
---

# 造价评估 Skill

## 何时启用

- 用户要做软件造价评估（forward 或 reverse）
- 用户输入 "造价评估" / "功能点估算" / "软件成本" / "NESMA"
- 用户运行 `/cost` 启动 Web 界面后

## 使用流程

1. 用户调用 `/cost` 命令（由 commands/cost.md 处理）启动后端 + 打开浏览器
2. 用户在 FP 编辑页点 "AI 辅助提取" 时本 Skill 自动激活：
   - 通过 GET `/api/projects/{id}` 拿到项目元信息（mode/city/industry/stage）
   - 通过 GET `/api/projects/{id}/uploads` 拿到上传文件清单
   - 读取项目目录 `~/.claude/projects/cost-estimation/uploads/{project_id}/*.{pdf,docx,xlsx}`
   - 按 NESMA 估算法生成 FP 初稿（参考 reference/nesma-rules.md）
   - 调用 POST `/api/projects/{id}/functions/bulk` 写回（每条带 `source: "ai_extracted"`）
3. 反向模式："AI 辅助分摊" 时本 Skill 同样激活：
   - 通过 GET `/api/projects/{id}/results` 拿到反算的目标 US（人时）
   - 调用 POST `/api/calc/allocate` 拿到分摊结果（含 `audit_tag: "budget_derived"` 标记）

## 不要做的事

- 不在会话里逐个询问 FP 项（让用户在 Web 表格里编辑）
- 不修改 `params_global` 表（始终用 `PATCH /api/projects/{id}/params/override`）
- 不直接生成 Excel；调用 `GET /api/reports/excel/{project_id}`
- 不主动启动后端（由 `/cost` 命令负责）
- 不绕过 token 鉴权（所有 `/api/*` 请求必须携带 `X-Auth-Token` 或 `?t=` 查询）

## 调用 API 时的鉴权

读取 token：
```bash
TOKEN=$(cat ~/.claude/projects/cost-estimation/.token)
PORT=$(cat ~/.claude/projects/cost-estimation/.port)
curl -H "X-Auth-Token: $TOKEN" "http://127.0.0.1:$PORT/api/projects"
```

## 参考文件

- `reference/nesma-rules.md` — NESMA 估算 5 大类详细规则
- `reference/csbmk-overview.md` — CSBMK®-202510 数据集结构与字段说明
```

- [ ] **Step 4: 创建 reference/nesma-rules.md**

```markdown
# NESMA 估算法规则（v2.3 简化版，对齐 GB/T 36964 附录）

NESMA（Netherlands Software Metrics Association）估算法把功能项分为 5 大类，按"未调整功能点（UFP）"权重打分。本仓库实现 NESMA 估算变体（不含详细数据元素 DET / 文件类型引用 FTR 计数），按"低/中/高"复杂度三档赋值。

## 5 大类与权重

| 类别 | 全称 | 含义 | 复杂度（低/中/高 UFP） |
|---|---|---|---|
| **EI** | External Input | 外部输入：用户提交数据更新内部数据（增/改/删） | 3 / 4 / 6 |
| **EO** | External Output | 外部输出：含派生计算的对外输出（报表、统计） | 4 / 5 / 7 |
| **EQ** | External Inquiry | 外部查询：检索数据但不含派生计算（搜索、列表） | 3 / 4 / 6 |
| **ILF** | Internal Logical File | 内部逻辑文件：应用维护的核心实体（用户、订单） | 7 / 10 / 15 |
| **EIF** | External Interface File | 外部接口文件：跨系统引用的只读数据 | 5 / 7 / 10 |

NESMA 估算（Estimated）默认所有项取"中"档权重；如需更细，按下方 DET/FTR 阈值调整。

## 复杂度判定（详尽计数模式）

### EI / EO / EQ 复杂度（基于 DET + FTR）

| FTR \ DET | 1-4 | 5-15 | ≥16 |
|---|---|---|---|
| 0-1 | 低 | 低 | 中 |
| 2 | 低 | 中 | 高 |
| ≥3 | 中 | 高 | 高 |

### ILF / EIF 复杂度（基于 DET + RET）

| RET \ DET | 1-19 | 20-50 | ≥51 |
|---|---|---|---|
| 1 | 低 | 低 | 中 |
| 2-5 | 低 | 中 | 高 |
| ≥6 | 中 | 高 | 高 |

DET = Data Element Types（字段数）  
FTR = File Types Referenced（引用的文件数）  
RET = Record Element Types（子记录类型数）

## 类别识别提示

读用户文档（功能清单/用户手册）时，按以下关键词归类：

- **EI**：「新增」「修改」「删除」「批量导入」「保存」「提交表单」「上传文件并存库」
- **EO**：「报表」「图表」「日报/月报」「导出 Excel（含计算）」「KPI 仪表盘」
- **EQ**：「查询」「搜索」「筛选」「列表展示」「详情查看」「下拉选项」
- **ILF**：「<实体>管理」（如用户管理 → User ILF）；新建一类核心数据
- **EIF**：「调用<外部系统>接口获取……」「读取来自……的字典数据」

## NESMA 估算模式（本系统默认）

启用 estimated 模式时：
- EI = 4 UFP / EO = 5 UFP / EQ = 4 UFP / ILF = 10 UFP / EIF = 7 UFP（中复杂度）
- 重用率（reuse_ratio）默认 0.0，修改率（modify_ratio）默认 0.0
- US（unadjusted size）= UFP × (1 - reuse_ratio × 0.5 - modify_ratio × 0.25)

实施规程附录 A 模板（功能点计数表）的列：
| 子系统 | 一级模块 | 二级模块 | 描述 | 类别 | UFP | 重用率 | 修改率 | US |

## 写回到 API

调用 `POST /api/projects/{id}/functions/bulk`，body：

```json
{
  "items": [
    {
      "subsystem": "用户子系统",
      "module_l1": "用户管理",
      "module_l2": "新增用户",
      "description": "管理员新增用户并设置角色",
      "category": "EI",
      "ufp": 4,
      "reuse_ratio": 0.0,
      "modify_ratio": 0.0,
      "source": "ai_extracted"
    }
  ]
}
```

> 后端会按 NESMA 计算 US 并写入触发器快照。
```

- [ ] **Step 5: 创建 reference/csbmk-overview.md**

```markdown
# CSBMK®-202510 数据集说明

CSBMK®（China Software Benchmarking Data）是中国软件行业基准数据，本仓库内置 2025 年 10 月版本（CSBMK®-202510）。

## 行业列表（7 项）

| 行业 | dev P50 (FP/PM) | ops P50 (FP/PM) |
|---|---|---|
| 全行业 | 6.72 | 0.74 |
| 电子政务 | 6.41 | — |
| 金融 | 10.46 | — |
| 电信 | 9.98 | — |
| 制造 | 7.69 | — |
| 能源 | 7.30 | — |
| 交通 | 6.86 | — |

> ops 仅"全行业"档完整，其他行业用全行业档兜底。

## 城市分级（37 城）

按软件工程师人月费率分为 A–E 五档：

| 档 | 代表城市 | dev 元/人月 |
|---|---|---|
| A | 北京 / 上海 / 深圳 | 31000–32200 |
| B | 杭州 / 苏州 / 南京 / 广州 / 西安 / 成都 / 厦门 / 福州 / 宁波 | 25000–28800 |
| C | 武汉 / 合肥 / 长沙 / 重庆 / 沈阳 / 大连 / 青岛 / 济南 / 哈尔滨 / 昆明 / 太原 / 南昌 / 南宁 / 海口 / 拉萨 / 贵阳 / 天津 | 22500–25000 |
| D | 长春 / 郑州 / 兰州 / 西宁 / 乌鲁木齐 / 石家庄 | 20000–22500 |
| E | 呼和浩特 / 银川 | <20000 |

## 调整因子（开发 5 项 + 运维 11 项）

### 开发因子

| 因子 | 取值范围 | 说明 |
|---|---|---|
| `app_type` | 1.00 (业务处理) – 2.00 (流程控制) | 应用类型 |
| `integrity_level` | 1.00 (C/D) – 1.30 (A 全周期) | 完整性等级 |
| `non_func` | 累加：分布式 / 性能 / 可靠性 / 多站点 各 +0.025 | 非功能需求 |
| `platform` | 0.6 (PowerBuilder/ASP) – 1.5 (C) | 编程语言/平台 |
| `team_bg` | 0.8 (同行业) – 1.2 (无背景) | 团队行业背景 |

### 运维因子

| 因子 | 取值范围 | 说明 |
|---|---|---|
| `update_freq` | 0.95 (季度) – 1.12 (频繁) | 更新频率 |
| `support` | 0.89 (远程) – 1.08 (纯现场) | 支持模式 |
| `security_level` | 0.90 (L1) – 1.10 (L5) | 等保等级 |
| `business_importance` | 0.90 (外围) – 1.10 (核心) | 业务重要性 |
| `response_time` | 0.90 (72h) – 1.10 (24h) | 响应时效 |
| `integrity_level` | 1.00 (C/D) – 1.30 (A 全周期) | 完整性等级 |
| `team_exp` | 0.80 (同行业) – 1.20 (无背景) | 团队经验 |
| `automation` | 0.90 (自动) – 1.10 (手工) | 自动化程度 |
| `deployment` | 1.00 (集中) – 1.06 (分布式) | 部署模式 |
| `user_scale` | 0.90 (≤1k) – 1.10 (>10k) | 用户规模 |
| `system_relevance` | 0.97 (无) – 1.14 (≥6) | 关联系统数 |

## CF 阶段调整因子

| 阶段 | CF | 含义 |
|---|---|---|
| budget | 1.39 | 预算 |
| bidding | 1.21 | 招投标 |
| planning | 1.10 | 立项 |
| change | 1.10 | 变更 |
| settled | 1.00 | 结算 |

## 公式速查

```
S（调整后规模）  = sum(US_i) × CF_stage
EFF_dev（人月） = S × PDR_dev × dev_factor_product
EFF_ops（人月） = S × PDR_ops × ops_factor_product   （仅在含运维时）
COST           = (EFF_dev + EFF_ops) × hours_per_pm × city_rate / hours_per_pm
                = (EFF_dev + EFF_ops) × city_rate（按人月直接乘）
```

> hours_per_pm = 174（CSBMK®-202510 默认）  
> 三档（P10/P50/P90）对应不同 PDR 取值，对应"乐观/中位/保守"语义。
```

- [ ] **Step 6: 跑测试验证通过**

```bash
python3 -m pytest tests/skill_smoke_test.py -v
# 期望: 5 用例 PASS
```

- [ ] **Step 7: Commit**

```bash
git add SKILL.md reference/ tests/skill_smoke_test.py
git commit -m "feat(skill): SKILL.md + nesma-rules.md + csbmk-overview.md (AI 提取触发与规则)"
```

---

## Task 5: 安装 preflight 脚本

**Files:**
- Create: `server/app/preflight.py`
- Modify: `commands/setup.md`（用 preflight.py 替换内联检测）
- Test: `server/tests/integration/test_preflight.py`

- [ ] **Step 1: 写 preflight 测试**

```python
# server/tests/integration/test_preflight.py
"""集成：preflight 检测 Python 版本、libmagic、pip 镜像可达性。"""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest
from click.testing import CliRunner


def test_preflight_passes_on_supported_python():
    from app.preflight import cli

    runner = CliRunner()
    result = runner.invoke(cli, [])
    # 当前 venv 已经满足，预期 exit 0 或 warning（但非 fatal）
    assert result.exit_code == 0
    assert "Python" in result.output


def test_preflight_fails_on_old_python(monkeypatch):
    from app import preflight

    monkeypatch.setattr(preflight.sys, "version_info", (3, 9, 0, "final", 0))
    runner = CliRunner()
    result = runner.invoke(preflight.cli, [])
    assert result.exit_code != 0
    assert "3.11" in result.output


def test_preflight_warns_when_libmagic_missing():
    from app import preflight

    with patch.object(preflight, "_find_libmagic", return_value=None):
        runner = CliRunner()
        result = runner.invoke(preflight.cli, [])
        assert result.exit_code != 0
        assert "libmagic" in result.output.lower()
```

- [ ] **Step 2: 跑测试验证失败**

```bash
cd server && /Users/renzhongyuan/WorkData/项目/2026/造价应用/server/.venv/bin/pytest tests/integration/test_preflight.py -v
```

- [ ] **Step 3: 实现 server/app/preflight.py**

```python
"""安装前置检查：Python 版本、libmagic、pip 镜像。"""
from __future__ import annotations

import ctypes.util
import sys
import urllib.error
import urllib.request
from typing import Optional

import click

MIN_PYTHON = (3, 11)
PIP_MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple/"
PIP_MIRROR_TIMEOUT = 5.0


def _find_libmagic() -> Optional[str]:
    return ctypes.util.find_library("magic")


def _probe_url(url: str, timeout: float) -> bool:
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except (urllib.error.URLError, OSError):
        return False


@click.command()
def cli() -> None:
    """运行安装前置检查。"""
    failed = False

    # 1. Python 版本
    cur = sys.version_info[:2]
    if cur < MIN_PYTHON:
        click.echo(
            f"✗ Python 版本过低: {cur[0]}.{cur[1]} < 3.11",
            err=True,
        )
        failed = True
    else:
        click.echo(f"✓ Python {cur[0]}.{cur[1]}")

    # 2. libmagic
    lib = _find_libmagic()
    if lib is None:
        click.echo(
            "✗ 未找到 libmagic："
            "macOS 用 `brew install libmagic`；"
            "Ubuntu/Debian 用 `apt install libmagic1`；"
            "RHEL/CentOS 用 `yum install file-libs`",
            err=True,
        )
        failed = True
    else:
        click.echo(f"✓ libmagic: {lib}")

    # 3. pip 镜像可达性（可选，仅 warning）
    if _probe_url(PIP_MIRROR, PIP_MIRROR_TIMEOUT):
        click.echo(f"✓ pip 镜像可达: {PIP_MIRROR}")
    else:
        click.echo(
            f"⚠ pip 镜像不可达: {PIP_MIRROR}（将回退默认源；如安装慢请检查网络）",
        )

    if failed:
        sys.exit(1)
    click.echo("✓ Preflight 全部通过。")


if __name__ == "__main__":
    cli()
```

- [ ] **Step 4: 跑测试验证通过**

```bash
cd server && /Users/renzhongyuan/WorkData/项目/2026/造价应用/server/.venv/bin/pytest tests/integration/test_preflight.py -v
# 期望: 3 用例 PASS
```

- [ ] **Step 5: 修改 commands/setup.md 改用 preflight.py**

把 setup.md 第 2 步替换为：

```markdown
2. 在 `$PLUGIN_DIR/server` 下用 venv 跑 preflight：
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
```

> 注意：preflight 需要 `click` 已安装；先 `pip install click --quiet` 再调用。原本的"创建 venv + pip install -r requirements.txt"放到第 4 步后面执行。

- [ ] **Step 6: Commit**

```bash
git add server/app/preflight.py server/tests/integration/test_preflight.py commands/setup.md
git commit -m "feat(plugin): preflight (python version + libmagic + pip mirror) integrated into setup"
```

---

## Task 6: Playwright E2E（forward + reverse 完整流程）

**Files:**
- Create: `web/playwright.config.ts`
- Create: `web/tests/e2e/forward.spec.ts`
- Create: `web/tests/e2e/reverse.spec.ts`
- Create: `web/tests/e2e/fixtures.ts`
- Modify: `web/package.json`（追加 `@playwright/test` 与 `test:e2e` 脚本）
- Test: 运行 `pnpm test:e2e`

- [ ] **Step 1: 在 web/ 安装 Playwright**

```bash
cd web
pnpm add -D @playwright/test@^1.45
pnpm exec playwright install chromium
```

- [ ] **Step 2: 创建 web/playwright.config.ts**

```ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:8788",
    trace: "retain-on-failure",
    video: "retain-on-failure",
    screenshot: "only-on-failure",
    extraHTTPHeaders: {
      "X-Auth-Token": process.env.E2E_AUTH_TOKEN ?? "e2e-token",
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
```

- [ ] **Step 3: 创建 web/tests/e2e/fixtures.ts**

```ts
import { test as base, expect } from "@playwright/test";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

type CostFixtures = {
  freshProject: { id: number; name: string };
};

export const test = base.extend<CostFixtures>({
  freshProject: async ({ request, baseURL }, use) => {
    const name = `e2e-${Date.now()}`;
    const created = await request.post(`${baseURL}/api/projects`, {
      headers: { "X-Auth-Token": TOKEN },
      data: {
        name,
        mode: "forward",
        city: "北京",
        industry: "电子政务",
        stage: "bidding",
      },
    });
    expect(created.ok()).toBeTruthy();
    const body = await created.json();
    const id = body.data.id;

    await use({ id, name });

    // teardown
    await request.delete(`${baseURL}/api/projects/${id}`, {
      headers: { "X-Auth-Token": TOKEN },
    });
  },
});

export { expect };
```

- [ ] **Step 4: 创建 web/tests/e2e/forward.spec.ts**

```ts
import { test, expect } from "./fixtures";

test.describe("Forward 模式完整流程", () => {
  test("从项目列表 → FP 编辑 → 计算结果 → 下载 Excel", async ({
    page,
    freshProject,
    baseURL,
    request,
  }) => {
    // 0. 浏览器把 token 拼到 URL
    const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";
    await page.goto(`${baseURL}/?t=${TOKEN}`);

    // 1. 项目列表能看到刚刚创建的项目
    await expect(page.getByRole("heading", { name: "项目列表" })).toBeVisible();
    await expect(page.getByText(freshProject.name)).toBeVisible();

    // 2. 跳到 FP 编辑
    const apiBulk = await request.post(
      `${baseURL}/api/projects/${freshProject.id}/functions/bulk`,
      {
        headers: { "X-Auth-Token": TOKEN },
        data: {
          items: [
            { subsystem: "用户子系统", module_l1: "登录", category: "EI", ufp: 4, reuse_ratio: 0, modify_ratio: 0, source: "manual" },
            { subsystem: "用户子系统", module_l1: "注册", category: "EI", ufp: 4, reuse_ratio: 0, modify_ratio: 0, source: "manual" },
            { subsystem: "订单子系统", module_l1: "下单", category: "EI", ufp: 4, reuse_ratio: 0, modify_ratio: 0, source: "manual" },
            { subsystem: "订单子系统", module_l1: "查询", category: "EQ", ufp: 4, reuse_ratio: 0, modify_ratio: 0, source: "manual" },
            { subsystem: "数据", module_l1: "用户", category: "ILF", ufp: 10, reuse_ratio: 0, modify_ratio: 0, source: "manual" },
          ],
        },
      },
    );
    expect(apiBulk.ok()).toBeTruthy();

    await page
      .getByRole("link", { name: "项目列表" })
      .or(page.getByRole("button", { name: /打开/ }))
      .first()
      .click();
    // 不同实现可能在卡片上点"打开"
    if (await page.locator(`text=${freshProject.name}`).count()) {
      await page.click(`text=${freshProject.name} >> .. >> text=打开`);
    }

    await expect(page.getByText(/FP 编辑.*#/)).toBeVisible();
    await expect(page.locator("table tbody tr")).toHaveCount(5);

    // 3. 跳到结果页
    await page.getByRole("button", { name: "计算 → 结果页" }).click();

    await expect(page.getByText(/评估结果.*正向/)).toBeVisible();

    // 4. 三档卡片渲染
    const cards = page.locator("[data-band]");
    await expect(cards).toHaveCount(3);
    await expect(page.locator("[data-band='P50'][data-recommended='true']")).toBeVisible();
    await expect(page.locator("[data-band='P50']")).toContainText(/万元/);

    // 5. 下载 Excel
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /下载 Excel 报告/ }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain(".xlsx");
  });
});
```

- [ ] **Step 5: 创建 web/tests/e2e/reverse.spec.ts**

```ts
import { test, expect } from "./fixtures";

test.describe("Reverse 模式完整流程", () => {
  test("从向导创建 reverse 项目 → 输入目标金额 → 反算 → 三档 FP", async ({
    page,
    baseURL,
    request,
  }) => {
    const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";
    await page.goto(`${baseURL}/?t=${TOKEN}`);

    // 1. 创建 reverse 项目（接口创建以加快 e2e）
    const created = await request.post(`${baseURL}/api/projects`, {
      headers: { "X-Auth-Token": TOKEN },
      data: {
        name: `e2e-rev-${Date.now()}`,
        mode: "reverse",
        city: "北京",
        industry: "电子政务",
        stage: "bidding",
      },
    });
    const body = await created.json();
    const id = body.data.id;

    try {
      // 2. 直接进入结果页
      await page.goto(`${baseURL}/projects/${id}/result?t=${TOKEN}`);
      await expect(page.getByText(/评估结果.*反向/)).toBeVisible();

      // 3. 填入目标金额并反算
      await page.getByLabel(/目标总造价/).fill("500000");
      await page.getByLabel(/其他费用/).fill("50000");
      await page.getByRole("button", { name: /^反算$/ }).click();

      // 4. 三档 FP 卡片
      await expect(page.locator("[data-band]")).toHaveCount(3);
      await expect(page.locator("[data-band='P10']")).toContainText(/FP/);
      await expect(page.locator("[data-band='P50']")).toContainText(/FP/);
      await expect(page.locator("[data-band='P90']")).toContainText(/FP/);
    } finally {
      // teardown
      await request.delete(`${baseURL}/api/projects/${id}`, {
        headers: { "X-Auth-Token": TOKEN },
      });
    }
  });
});
```

- [ ] **Step 6: 修改 web/package.json 加 e2e 脚本**

在 scripts 中追加：

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui"
  },
  "devDependencies": {
    "@playwright/test": "^1.45.0"
  }
}
```

- [ ] **Step 7: 文档化 E2E 启动步骤（写入 web/README.md）**

在 web/README.md 末尾追加：

```markdown
## E2E 测试

E2E 测试需要后端启动 + web/dist 构建产物：

```bash
# 终端 1：先 build web
pnpm build

# 终端 2：启动后端（用固定 token "e2e-token"）
cd ../server
AUTH_TOKEN=e2e-token \
COST_WEB_DIST_DIR=$(realpath ../web/dist) \
COST_DATABASE_URL=sqlite:///$(mktemp -u)-cost.sqlite \
.venv/bin/python -m app.bootstrap \
  --db /tmp/cost-e2e.sqlite \
  --seed app/data/csbmk_202510.json
AUTH_TOKEN=e2e-token \
COST_DATABASE_URL=sqlite:////tmp/cost-e2e.sqlite \
COST_WEB_DIST_DIR=$(realpath ../web/dist) \
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8788

# 终端 3：跑 e2e
cd ../web
E2E_AUTH_TOKEN=e2e-token pnpm test:e2e
```
```

- [ ] **Step 8: 跑 E2E 验证**

```bash
# 按 Step 7 的指令启动后端 + web build + dist 挂载
# 然后：
cd web && E2E_AUTH_TOKEN=e2e-token pnpm test:e2e
# 期望: 2 个 spec 全部 PASS
```

> 如果 e2e 因 web/dist 未 build 而报 404，先 `pnpm build`；如果因 token 不匹配 401，确认 AUTH_TOKEN 与 E2E_AUTH_TOKEN 完全一致。

- [ ] **Step 9: Commit**

```bash
cd /Users/renzhongyuan/WorkData/项目/2026/造价应用
git add web/playwright.config.ts web/tests/e2e/ web/package.json web/pnpm-lock.yaml web/README.md
git commit -m "test(e2e): playwright forward + reverse full flow with token + fixtures"
```

---

## Task 7: mutation testing（mutmut on core/）

**Files:**
- Modify: `server/pyproject.toml`（追加 `[tool.mutmut]` 配置）
- Create: `server/scripts/run_mutmut.sh`
- Create: `docs/mutation-report.md`（首次运行的报告快照）

- [ ] **Step 1: 配置 mutmut**

在 `server/pyproject.toml` 末尾追加：

```toml
[tool.mutmut]
paths_to_mutate = "app/core/"
backup = false
runner = "pytest -x -q"
tests_dir = "tests/"
```

- [ ] **Step 2: 创建 server/scripts/run_mutmut.sh**

```bash
#!/bin/bash
# Mutation testing for core/ — 目标杀死率 ≥ 70%
set -euo pipefail

cd "$(dirname "$0")/.."

echo "→ 清理上次结果"
rm -rf .mutmut-cache mutants

echo "→ 跑 mutmut（约 5–10 分钟）"
./.venv/bin/mutmut run --paths-to-mutate app/core/ || true

echo "→ 汇总结果"
./.venv/bin/mutmut results
./.venv/bin/mutmut junitxml > mutants.xml

echo "→ 计算杀死率"
KILLED=$(./.venv/bin/mutmut results | grep -oE '[0-9]+ killed' | grep -oE '[0-9]+' | head -1)
SURVIVED=$(./.venv/bin/mutmut results | grep -oE '[0-9]+ survived' | grep -oE '[0-9]+' | head -1)
TOTAL=$((KILLED + SURVIVED))
if [ "$TOTAL" -gt 0 ]; then
  PERCENT=$((KILLED * 100 / TOTAL))
  echo "✓ 杀死率: $KILLED / $TOTAL = $PERCENT%"
  if [ "$PERCENT" -lt 70 ]; then
    echo "⚠ 杀死率 < 70%，建议增强 core/* 测试"
    exit 1
  fi
else
  echo "⚠ 未生成 mutant"
  exit 1
fi
```

- [ ] **Step 3: chmod + x**

```bash
chmod +x server/scripts/run_mutmut.sh
```

- [ ] **Step 4: 跑 mutmut（耗时较久，先尝试一次）**

```bash
cd server && bash scripts/run_mutmut.sh
```

> 此 step 预计 5–10 分钟。如果中途因测试不稳定被 mutmut 误判，记录到 docs/mutation-report.md 的 known-issues。

- [ ] **Step 5: 把首次报告快照写到 docs/mutation-report.md**

模板：

```markdown
# Mutation Testing Report (首次基线)

**日期**：YYYY-MM-DD（实际跑出的日期）  
**目标范围**：`server/app/core/{forward.py, reverse.py, allocator.py, factors.py, evaluation_context.py}`  
**目标杀死率**：≥ 70%

## 结果

```text
（粘贴 `mutmut results` 的最终输出，至少含 killed/survived/total）
```

## 杀死率

- killed: <N>
- survived: <M>
- 杀死率：N / (N+M) × 100% = X%

## 存活变异（survived）

> 选 5–10 条最值得关注的列出，以及对应的修复建议（增加测试 / 重构使更可测）

| Mutant ID | 文件:行 | 类型 | 解释 |
|---|---|---|---|
| `core.forward.x_1` | forward.py:42 | 算术运算变异 | ... |

## 已知 false positives

> 例如某些日志分支的变异可接受 surviving

## 维护

- 重新运行：`bash server/scripts/run_mutmut.sh`
- 查看具体 mutant：`mutmut show <id>`
```

- [ ] **Step 6: Commit**

```bash
cd /Users/renzhongyuan/WorkData/项目/2026/造价应用
git add server/pyproject.toml server/scripts/run_mutmut.sh docs/mutation-report.md
git commit -m "test(mutation): mutmut config + run script + first baseline report"
```

> 如果 mutmut 杀死率 < 70%，把缺口写进 docs/mutation-report.md，并在后续 polish task 补 core/ 测试；不阻塞 plan 4。

---

## Task 8: 用户与开发者文档

**Files:**
- Create: `README.md`（仓库根，覆盖如已存在 placeholder）
- Create: `docs/user-guide.md`
- Create: `docs/dev-guide.md`
- Create: `docs/troubleshooting.md`

- [ ] **Step 1: 检查现有 README.md**

```bash
ls -la /Users/renzhongyuan/WorkData/项目/2026/造价应用/README.md 2>/dev/null
```

如已有同名占位则可覆盖；本任务以"创建/覆盖"对待。

- [ ] **Step 2: 创建仓库根 README.md**

```markdown
# 软件造价制作系统

基于 GB/T 36964 / T/CCUA 005-2024 / GB/T 28827.7-2022 / GB/T 42452-2023 与 CSBMK®-202510 数据集的软件造价评估工具，作为 Claude Code Plugin 发布。

## 功能

- ✅ **正向模式**（功能点 → 成本）：上传需求文档 → AI 提取 FP → 三档成本估算
- ✅ **反向模式**（目标成本 → 功能点）：输入预算 → 反推三档 FP → AI 分摊到模块
- ✅ **NESMA 估算法**（默认）：EI/EO/EQ/ILF/EIF 5 类、低中高复杂度
- ✅ **6 行业 + 37 城**生产率与费率（CSBMK®-202510 内置）
- ✅ **17+ 调整因子**：开发因子 5 项 + 运维因子 11 项 + CF 阶段因子
- ✅ **Excel 报告**：7 Sheet 模板（封面/摘要/报告书/调整因子/FP 表/详细计算/参数附录）
- ✅ **本地隔离**：只绑 127.0.0.1，token + Origin + CORS 三层防护

## 一键安装

```bash
# 在 Claude Code 中：
/plugin marketplace add github.com/your-org/cost-estimation
/plugin install cost-estimation
/cost-estimation:setup
/cost
```

详见 [docs/user-guide.md](docs/user-guide.md)。

## 目录结构

```
.
├── .claude-plugin/         # Plugin 元信息
├── commands/               # slash 命令（setup/cost/cost-stop）
├── reference/              # NESMA 规则 + CSBMK 说明
├── server/                 # FastAPI 后端 + 计算引擎
│   ├── app/
│   │   ├── core/           # 算法核心（forward/reverse/allocator）
│   │   ├── api/            # REST 路由
│   │   ├── parsers/        # PDF/Word/Excel 解析
│   │   ├── exporters/      # Excel 渲染
│   │   └── data/csbmk_202510.json
│   └── tests/              # pytest（单元 + 集成 + 黄金）
├── web/                    # Vue 3 前端 + Vitest + Playwright E2E
├── docs/
│   ├── user-guide.md       # 用户手册
│   ├── dev-guide.md        # 开发者指南
│   ├── troubleshooting.md  # 故障排查
│   ├── mutation-report.md  # 变异测试报告
│   └── superpowers/        # 设计与实施计划存档
└── SKILL.md                # AI 提取触发与规则
```

## 开发

```bash
# 后端
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest --cov=app

# 前端
cd web
pnpm install
pnpm test
pnpm dev      # 开发服务器（vite proxy 后端 8788）

# E2E
pnpm test:e2e
```

详见 [docs/dev-guide.md](docs/dev-guide.md)。

## 标准合规

- GB/T 36964-2018 软件工程 软件开发成本度量规范
- T/CCUA 005-2024 软件研发成本度量规范实施指南
- GB/T 28827.7-2022 信息技术服务 运行维护 第7部分：成本度量规范
- GB/T 42452-2023 软件工程 软件开发成本度量规范 应用指南
- CSBMK®-202510 中国软件行业基准数据 2025 年 10 月版

## License

MIT
```

- [ ] **Step 3: 创建 docs/user-guide.md**

```markdown
# 用户手册

## 安装

### 前置条件

- macOS 11+ / Ubuntu 20.04+ / Windows 10+（WSL2）
- Python 3.11+
- libmagic（macOS: `brew install libmagic`；Ubuntu: `apt install libmagic1`）
- Node.js 20+ + pnpm 9（仅开发模式需要）
- Claude Code 1.0+

### 步骤

```bash
# 1. 添加 marketplace
/plugin marketplace add github.com/your-org/cost-estimation

# 2. 安装 plugin（自动下载到 ~/.claude/plugins/cache/cost-estimation）
/plugin install cost-estimation

# 3. 首次初始化（建 venv + 装依赖 + 建库 + seed CSBMK）
/cost-estimation:setup
```

预期输出：

```
✓ Python 3.12.4
✓ libmagic: /opt/homebrew/lib/libmagic.dylib
✓ pip 镜像可达
✓ Preflight 全部通过。
（pip install 输出...）
✓ 已装载 CSBMK seed（版本 CSBMK®-202510）。
✓ 数据库初始化完成: ~/.claude/projects/cost-estimation/db/cost.sqlite
✓ 安装完成。运行 /cost 即可启动 Web 界面
```

## 日常使用

### 启动

```bash
/cost
```

预期：浏览器自动打开 `http://127.0.0.1:8788/?t=<token>`，进入项目列表页。

### 正向模式（功能点 → 成本）

1. 点"新建项目"，5 步向导：模式选 forward → 名称 → 城市/行业 → 阶段 → 确认
2. 在 FP 编辑屏：
   - 点"上传文档让 AI 写第一稿"，上传需求清单（PDF/Word/Excel）
   - AI 解析后自动写入功能点（每条带 source=ai_extracted 标记）
   - 在表格里微调（增删改）
3. 点"参数管理"可调整任一因子（覆盖项有"自定义"徽章高亮）
4. 点"计算 → 结果页"查看三档金额（P10 乐观 / P50 中位推荐 / P90 保守）
5. 点"下载 Excel 报告"获得 7-Sheet xlsx

### 反向模式（目标成本 → 功能点）

1. 新建项目时选 reverse 模式
2. 直接进入结果页，输入目标总造价 + 其他费用，点"反算"
3. 系统按 P10/P50/P90 三档生产率反推 FP 数
4. 采纳推荐档（P50 默认）后，可在 FP 编辑屏看到 source=allocator 的"预算倒推"行
5. AI 辅助分摊会把总 FP 拆到模块（在 FP 表格中可微调）
6. 计算 → 验证反算回去与目标金额误差 ≤ 1%
7. 下载 Excel（封面页含"反向模式"水印）

### 停止

```bash
/cost-estimation:cost-stop
```

## 数据位置

- 数据库：`~/.claude/projects/cost-estimation/db/cost.sqlite`
- 上传文件：`~/.claude/projects/cost-estimation/uploads/<project_id>/`
- Excel 导出：`~/.claude/projects/cost-estimation/exports/`
- 一次性 token：`~/.claude/projects/cost-estimation/.token`（启动时生成、停止时清除）

## 备份与导出

直接复制 `~/.claude/projects/cost-estimation/db/cost.sqlite` 即可备份所有数据。

## 卸载

```bash
/plugin uninstall cost-estimation
rm -rf ~/.claude/projects/cost-estimation
```

## 常见问题

见 [troubleshooting.md](troubleshooting.md)。
```

- [ ] **Step 4: 创建 docs/dev-guide.md**

```markdown
# 开发者指南

## 仓库结构

```
.
├── server/                 # FastAPI + SQLite + 计算引擎
│   ├── app/
│   │   ├── core/           # 纯算法（forward/reverse/allocator/factors）
│   │   ├── api/            # REST 路由
│   │   ├── services/       # 业务逻辑（连接 core 和 db）
│   │   ├── db/             # SQLAlchemy 模型 + Alembic 迁移
│   │   ├── parsers/        # PDF/Word/Excel 解析
│   │   ├── exporters/      # Excel 渲染（命名区域 + fallback）
│   │   ├── schemas/        # Pydantic v2 DTO
│   │   ├── data/csbmk_202510.json
│   │   ├── bootstrap.py    # 一次性 DB 初始化 CLI
│   │   ├── preflight.py    # 安装前置检查
│   │   ├── deps.py         # 依赖注入 + token 中间件
│   │   ├── config.py       # Settings (pydantic-settings)
│   │   └── main.py         # create_app + 路由 mount + 静态托管
│   └── tests/
│       ├── unit/           # 单元测试
│       ├── integration/    # API + DB 集成
│       └── golden/         # 实施规程附录 D 算例
├── web/                    # Vue 3 + Vite + Pinia + Vitest + Playwright
└── docs/
```

## 后端开发

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 跑测试
pytest --cov=app --cov-report=term-missing  # 覆盖率 ≥ 80%

# 跑开发服务器
AUTH_TOKEN=devtoken \
uvicorn app.main:app --host 127.0.0.1 --port 8788 --reload
```

### 添加新 API

1. 在 `app/schemas/` 加 Pydantic 模型
2. 在 `app/services/` 加业务逻辑（接 db 与 core）
3. 在 `app/api/` 加 router（/api/...）
4. 在 `app/main.py` include router
5. 在 `tests/integration/` 写集成测试

### 添加新计算因子

1. 在 `app/core/factors.py` 加因子表 + 应用函数
2. 在 `app/data/csbmk_202510.json` 加默认值
3. 在 `tests/unit/test_factors.py` 写单测
4. 在 `app/core/forward.py` / `reverse.py` 调用
5. 黄金测试 `tests/golden/test_golden.py` 必须仍通过

## 前端开发

```bash
cd web
pnpm install
pnpm dev          # 启动开发服务器（http://127.0.0.1:5173/?t=devtoken）
pnpm test         # 单测
pnpm test:e2e     # E2E（需后端 + dist build）
pnpm build        # 生产构建到 web/dist/
```

### 添加新屏

1. 在 `src/views/` 加 Vue SFC
2. 在 `src/router/index.ts` 注册路由（含 props 函数）
3. 在 `src/stores/` 加 Pinia store（如需）
4. 在 `src/__tests__/views/` 写测试，覆盖 5 态矩阵

### 添加新组件

参考 `src/components/status/*.vue`：必须 ARIA + 触摸目标 ≥ 44px + oklch 颜色。

## 数据库迁移

```bash
cd server
alembic revision --autogenerate -m "add new column"
alembic upgrade head
```

注意：bootstrap.py 在首次运行时直接 `Base.metadata.create_all` 建库，不依赖 Alembic；生产升级走 Alembic。

## 黄金测试

`server/tests/golden/test_golden.py` 用 CSBMK®-202210 历史数据复算实施规程附录 D 算例，期望 489,180 元 ±100。任何 core/* 改动必须保持此测试通过。

## Mutation testing

```bash
cd server && bash scripts/run_mutmut.sh
```

杀死率目标 ≥ 70%（详见 docs/mutation-report.md）。

## 发布

1. 更新 `server/pyproject.toml` + `web/package.json` + `.claude-plugin/plugin.json` 的 version
2. 更新 `CHANGELOG.md`
3. tag + push
4. 在 marketplace 仓库更新 `marketplace.json` 的 plugin URL（指向新 tag）

## 关键设计决策

详见 `docs/superpowers/specs/2026-05-10-cost-estimation-design.md` 与 §16 /autoplan 评审报告。

## CI（推荐）

GitHub Actions（仓库未自动配置，建议自行加）：

```yaml
name: CI
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: sudo apt-get install -y libmagic1
      - working-directory: server
        run: |
          python -m venv .venv && source .venv/bin/activate
          pip install -r requirements.txt -e ".[dev]"
          pytest --cov=app
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with: { version: 9 }
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: pnpm }
      - working-directory: web
        run: |
          pnpm install --frozen-lockfile
          pnpm type-check
          pnpm lint
          pnpm test --run
```
```

- [ ] **Step 5: 创建 docs/troubleshooting.md**

```markdown
# 故障排查

## 安装阶段

### `python3: command not found`

→ macOS: `brew install python@3.11` 或 Ubuntu: `apt install python3.11 python3.11-venv`

### `Preflight ✗ libmagic 未找到`

→ macOS: `brew install libmagic`  
→ Ubuntu/Debian: `sudo apt-get install libmagic1`  
→ RHEL/CentOS: `sudo yum install file-libs`

### `pip install` 慢/卡住

→ 系统已默认使用清华镜像；如仍慢，编辑 `~/.pip/pip.conf` 加：
```
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
```
或临时 `pip install -i https://pypi.org/simple/ ...` 用官方源。

## 启动阶段

### `8788–8800 端口全部占用`

→ 用 `lsof -nP -iTCP:8788 -sTCP:LISTEN` 查谁在占用，按需停掉，再重跑 `/cost`。

### 浏览器打开后 401 Unauthorized

→ 确保 URL 含 `?t=<token>`（`/cost` 命令会自动拼接）。手动构造 URL 时去 `~/.claude/projects/cost-estimation/.token` 读 token。

### `/cost-stop` 后再次 `/cost` 启动失败

→ 检查是否有遗留 PID：`lsof -nP -iTCP:8788 -sTCP:LISTEN`；若有，`kill <pid>`。

## 计算阶段

### 反向模式提示 `BUDGET_NEGATIVE`

→ 输入的 `target_total - other_cost <= 0`。修正目标总造价或其他费用。

### Forward 模式三档结果差距太大

→ 多半是 PDR 三档跨度太大（电信行业 P10=2.4 vs P90=27.7）。如想收窄区间，进"参数管理 → 生产率"调 P10/P90。

### Excel 下载 500 错误

→ 看 `/tmp/cost-estimation.log`。常见原因：openpyxl 版本不兼容（升级 openpyxl）；模板被删（重跑 `/cost-estimation:setup`）。

## 数据丢失

### "我误删了项目"

→ 项目软删除策略：检查 SQLite `projects.deleted_at` 字段。如已硬删，从 `~/.claude/projects/cost-estimation/db/cost.sqlite.bak` 恢复（如有备份）。

### "FP 编辑误改了"

→ FP 表有 5 版历史快照，前端"参数管理 → 快照"Tab 可回滚（v1 实现仅查看，回滚 API `POST /api/projects/{id}/functions/restore?version=N`）。

## 卸载

```bash
/plugin uninstall cost-estimation
rm -rf ~/.claude/projects/cost-estimation
rm -rf ~/.claude/plugins/cache/cost-estimation
```

## 联系

issues: <repo-url>/issues
```

- [ ] **Step 6: Commit**

```bash
git add README.md docs/user-guide.md docs/dev-guide.md docs/troubleshooting.md
git commit -m "docs: README + user-guide + dev-guide + troubleshooting"
```

---

## 自检清单

- [ ] T1-T8 全部列出文件路径
- [ ] 每个 Task 都先写测试或校验脚本（除纯文档 T8）
- [ ] Plugin manifest 含 marketplace + plugin.json + 3 commands 引用
- [ ] commands/setup.md 含 preflight + venv + bootstrap
- [ ] commands/cost.md 含 token 生成 + 端口探测 + PID 写入 + 浏览器打开
- [ ] commands/cost-stop.md 含 PID kill + 清理 .token / .port
- [ ] SKILL.md 含触发短语 + API 调用规则 + "不要做的事"清单
- [ ] reference/nesma-rules.md 含 5 类 + 复杂度判定矩阵
- [ ] reference/csbmk-overview.md 含 7 行业 + 37 城 + 17 因子总览
- [ ] preflight.py 检测 Python/libmagic/pip 镜像
- [ ] Playwright 双 spec（forward + reverse）
- [ ] mutmut 配置 + 报告模板
- [ ] README + user-guide + dev-guide + troubleshooting 完整

---

## 执行选择

- **Subagent-Driven Execution（已选）**：每个 Task 派发一个 implementer subagent，紧接 spec/quality 双 reviewer，最终 final reviewer。
