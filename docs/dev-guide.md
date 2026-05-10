# 开发者指南

## 仓库结构

```
.
├── server/                 # FastAPI + SQLite + 计算引擎
│   ├── app/
│   │   ├── core/           # 纯算法（forward / reverse / allocator / factors）
│   │   ├── api/            # REST 路由
│   │   ├── services/       # 业务逻辑（连接 core 和 db）
│   │   ├── db/             # SQLAlchemy 模型 + Alembic 迁移
│   │   ├── parsers/        # PDF / Word / Excel 解析
│   │   ├── exporters/      # Excel 渲染（命名区域 + fallback）
│   │   ├── schemas/        # Pydantic v2 DTO
│   │   ├── data/csbmk_202510.json
│   │   ├── bootstrap.py    # 一次性 DB 初始化 CLI
│   │   ├── preflight.py    # 安装前置检查
│   │   ├── deps.py         # 依赖注入 + token 中间件
│   │   ├── config.py       # Settings (pydantic-settings, env_prefix=COST_)
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
COST_AUTH_TOKEN=devtoken \
COST_DB_PATH=$HOME/.claude/projects/cost-estimation/db/cost.sqlite \
COST_DATA_DIR=$HOME/.claude/projects/cost-estimation \
uvicorn app.main:app --host 127.0.0.1 --port 8788 --reload
```

> 所有运行期配置走 `COST_*` 前缀环境变量（见 `app/config.py` 的 `Settings` 类）。常用变量：
> - `COST_AUTH_TOKEN`：一次性鉴权 token（必填）
> - `COST_DB_PATH`：SQLite 文件路径
> - `COST_DATA_DIR`：用户数据根目录（uploads / exports / .token / .port 都在此）
> - `COST_WEB_DIST_DIR`：前端静态产物目录（生产模式由 main.py 静态挂载）

### 添加新 API

1. 在 `app/schemas/` 加 Pydantic 模型
2. 在 `app/services/` 加业务逻辑（接 db 与 core）
3. 在 `app/api/` 加 router（`/api/...`）
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
pnpm test         # 单测（Vitest）
pnpm test:e2e     # E2E（Playwright，需后端 + dist build）
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

注意：`bootstrap.py` 在首次运行时直接 `Base.metadata.create_all` 建库，不依赖 Alembic；生产升级走 Alembic。

## 黄金测试

`server/tests/golden/test_golden.py` 用 CSBMK®-202210 历史数据复算实施规程附录 D 算例，期望 489,180 元 ±100。任何 `core/*` 改动必须保持此测试通过。

## Mutation testing

```bash
cd server && bash scripts/run_mutmut.sh
```

杀死率目标 ≥ 70%（详见 [mutation-report.md](mutation-report.md)）。

## 发布

1. 更新 `server/pyproject.toml` + `web/package.json` + `.claude-plugin/plugin.json` 的 version
2. **构建前端产物**（必须）：
   ```bash
   cd web && pnpm install && pnpm build
   ```
3. **提交 web/dist/**：
   ```bash
   git add web/dist/
   git commit -m "build(web): produce dist for v<VERSION> release"
   ```
4. 更新 `CHANGELOG.md`（如有）
5. tag + push
6. 在 marketplace 仓库更新 `marketplace.json` 的 plugin URL（指向新 tag）

> 重要：因 plugin 通过 git clone 分发，**dist 必须随源码一起 commit**，否则用户 `/cost` 启动后浏览器空白。如忘记 build/commit dist，`commands/setup.md` 会尝试本地构建作为 fallback，但要求用户机器上有 Node.js 20+ 与 pnpm 9。

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
