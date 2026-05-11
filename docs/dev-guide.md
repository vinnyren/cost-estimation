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

## v2.0 架构新增

v2.0 围绕 11 个 GAP 闭环做了横向扩展（向后兼容，无 breaking change）。下文聚焦给开发者看的架构、调试、扩展点；用户向文档见 `README.md` 与 `user-guide.md`。

### 后端：3 张新表 + 3 个 migration

| Migration | 改动 | 涉及表 |
|---|---|---|
| `9b1c4f2e7a3d` | 在 `projects` 加两列 JSON | `projects.factors_dev_json` / `factors_ops_json`（项目级因子覆盖，NULL 时回落全局） |
| `a4d8e6c2b9f1` | 新表 `param_snapshots` | 全局参数快照（name / payload_json / created_at），用于 ParamManager 一键回滚 |
| `b7e2f1d9c4a8` | 新表 `audit_log` | 项目操作流水（project_id / action / actor / before_json / after_json / created_at），cursor 分页 |

> Schema 物理由 `app/db/models.py` 描述；migration 在 `app/db/migrations/versions/`。**bootstrap.py 仍走 `Base.metadata.create_all`，对新装用户透明；老库走 alembic upgrade head。**

### 后端：新 endpoint 簇

| 路由 | 功能 | 文件 |
|---|---|---|
| `POST /api/projects/{id}/copy` | 一键复制项目（含 functions / factors_overrides），返回新 id | `app/api/projects.py` |
| `GET /api/projects/{id}/audit?before_id=&limit=` | 审计列表，cursor 分页（before_id 比 offset 稳定） | `app/api/audit.py` |
| `GET/POST/PUT/DELETE /api/params/snapshots`、`POST /api/params/snapshots/{id}/restore` | 快照 CRUD + 还原 | `app/api/snapshots.py` |
| `GET /api/params/effective` | 全局参数视图（合并 seed + 用户覆盖 + 当前快照） | `app/api/params.py` |

`GET /api/projects` **查询参数升级**：新增 `q` / `city` / `industry` / `phase` / `mode` / `sort` / `order` / `page` / `size`，响应改为 envelope：

```json
{
  "items": [...],
  "meta": { "total": 137, "page": 1, "size": 20, "has_next": true }
}
```

> 老 client 传不带任何 query 时回退到旧行为（兼容）。

### 后端：关键中间件 / 服务层

**AuditMiddleware**（`app/middleware/audit.py`）
- 拦截 `PATCH/POST/PUT/DELETE /api/projects/*`
- 写 `audit_log`，actor 取自 `COST_AUTH_TOKEN` 哈希前 8 位（单租户系统）
- before/after diff 走 JSON Patch（仅保留变更字段，体积小）
- 失败 fail-open（不阻塞业务）

**Factors 组装层**（`services/factors.py`）
- `assemble_factors(project) -> (dev_factor, ops_factor)`
- 把 `project.factors_dev_json`（项目级）merge 进 `effective.factors_dev`（全局）
- 项目级覆盖项目，全局兜底，传给 `core/forward.py` / `core/reverse.py`
- **关键不变量**：core/ 层只接受 plain dict，不感知 db model；factors 组装是 services 的事

### 前端新增

**5 个新组件**（`web/src/components/`）：

| 组件 | 用途 |
|---|---|
| `AlphaSlider.vue` | 0/0.5/1 三档进度因子滑杆（含 keyboard a11y） |
| `FactorTable.vue` | 因子矩阵表格，dev/ops 双 tab |
| `FactorDropdown.vue` | 单因子下拉（带 tooltip 显示 CSBMK 默认） |
| `PhaseCfPreview.vue` | 阶段系数即时预览 |
| `ProjectActionMenu.vue` | 项目卡操作菜单（复制 / 审计 / 删除） |

**1 个新 view**：`AuditView.vue`（`/projects/:id/audit`），cursor 分页（before_id）+ 时间线展示。

**3 个新 api client**（`web/src/api/`）：`snapshots.ts` / `audit.ts` / `projects.ts` 扩展（list 接 meta envelope、copy 方法）。

**大改 view**：

| View | 改动 |
|---|---|
| `ProjectWizard.vue` | 5 步 → 7 步骨架（加 factors 配置 + 复核） |
| `ParamManager.vue` | 4 个 stub tab 全部实装（生产率 / 因子 / 阶段 / 快照 / 规模变更） |
| `ProjectList.vue` | 顶部 toolbar（搜索 + 行业/阶段/模式筛选） + 服务端分页 |
| `FpEditor.vue` | AI 提取 hint + polling 进度 |
| `ResultView.vue` | allocator panel（阶段分摊预览 + 导出） |

> **依赖瘦身**：v2.0 移除 element-plus（4.2MB），改为原生 HTML + scoped CSS，gzipped bundle -85%（≈ 180KB → 27KB）。

### Plugin 链路（GAP-A/C）

| 文件 | 用途 |
|---|---|
| `commands/cost.md` | 主工作流（启动 + 引导） |
| `commands/cost-allocate.md` | **新增**，阶段分摊向导，配合 ResultView 的 allocator |
| `SKILL.md` | NESMA 提取 prompt 增强（GAP-C 提升识别精度） |

### 调试 v2 新功能

```bash
# 看审计流水
sqlite3 ~/.claude/projects/cost-estimation/db/cost.sqlite \
  "SELECT created_at, action, project_id FROM audit_log ORDER BY id DESC LIMIT 20;"

# 看快照列表
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8788/api/params/snapshots

# 复算 effective params
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8788/api/params/effective | jq .
```

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
