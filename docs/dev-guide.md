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

v2.0 围绕 11 个 GAP 闭环（A-K）做了横向扩展，向后兼容、无 breaking change。下文聚焦给开发者看的架构、调试、扩展点；用户向文档见 `README.md` 与 `user-guide.md`，发布说明见 `v2-changelog.md`。

### 后端：3 张新表 + 3 个 migration

| Migration | 改动 | 涉及表 |
|---|---|---|
| `9b1c4f2e7a3d` | 在 `projects` 加两列 JSON | `factors_dev_json` / `factors_ops_json`（项目级因子选择，NULL 时 fallback 1.0 + Result.warning_messages 提示） |
| `a4d8e6c2b9f1` | 新表 `param_snapshots` | 列：`id / scope / label / created_at / payload_json`。scope = `"global"` 或 project_id；payload_json 是 effective_params 完整序列化 |
| `b7e2f1d9c4a8` | 新表 `audit_log` + 3 索引 | 列：`id / project_id (FK CASCADE) / ts / actor / action / target / diff_json`。3 索引：project_id / ts / (project_id, ts) 复合 |

> Schema 物理由 `app/db/models.py` 描述；migration 在 `server/alembic/versions/`。`alembic upgrade head` 自动应用；新装用户走 `Base.metadata.create_all` 一次性建表（migration revision 用 `alembic stamp head` 标记到最新）。

### 后端：新 endpoint 簇

| 路由 | 功能 | 文件 |
|---|---|---|
| `POST /api/projects/{id}/copy` | 项目复制（含 FunctionPoint + ParamOverride 行，不复制 Result / FPSnapshot / Upload），返回新 project | `app/api/projects.py` + `services/projects.py:copy_project` |
| `GET /api/projects/{id}/audit?before_id=&limit=` | 审计列表，cursor 分页（`id < before_id` order desc） | `app/api/audit.py` + `services/audit.py` |
| `POST /api/params/snapshots` / `GET` / `POST /{id}/restore` / `DELETE /{id}` | 参数快照 CRUD + restore | `app/api/snapshots.py` + `services/snapshots.py` |
| `GET /api/params/effective` | 全局 effective 视图（无项目作用域） | `app/api/params.py` |

`GET /api/projects` **查询参数升级**：新增 `q` / `city` / `industry` / `phase` / `mode` / `sort` / `order` / `page` / `size`，响应改为新 envelope：

```json
{
  "success": true,
  "data": [/* projects */],
  "error": null,
  "meta": { "total": 137, "page": 1, "size": 20 }
}
```

> 全部 query params 可选；缺省 = 不筛 / sort=created_at desc / page=1 size=50（max 200）。前端 `projectsApi.list()` 内部走 `query()` 包装，旧调用方透明兼容。

### 后端：关键中间件 / 服务层

**AuditMiddleware**（`app/middleware/audit.py`）
- 拦截 `PATCH/POST/PUT/DELETE /api/projects/*`
- 仅对 2xx 响应写 audit_log（4xx/5xx 不记）
- actor 字段当前硬编码 `"user"`（v3 多用户时切换为登录用户 ID，schema 已预留）
- `diff_json` 序列化 `{sub_path, query}`（query 自动剔除 `t=` auth token）；`project.copy` 还额外为副本写一条入口 `diff_json={"copied_from": ...}`
- `project.create` / `project.copy` 需要从响应 body 解析新 id，所以会 drain body_iterator 后用 `Response(content=body, ...)` 重建 — **streaming 响应 endpoint 必须 bypass middleware**（已加 in-line 警示）
- DB 写入用独立 `SessionLocal()`（不与请求 session 竞争）+ try/except 包住 — audit 失败永不影响业务

**Factors 组装层**（`services/factors.py`）
- `project_factors(project, effective_params) -> (dev_factor, ops_factor, warnings)`
- 读 `project.factors_dev_json` (用户选的 level 标签集合) + `effective.factors_dev` (CSBMK 标签→multiplier 表)，逐维度查表后调 `core.factors.dev_factor_chain` 拿 5 维乘积
- 缺失字段 / json 损坏 / label 不在表里 → fallback 1.0，对应 `warning_messages` 仅在整体 json 为空时附加
- ops 同理（11 维），但 `include_ops=False` 时即使 factors_ops 空也不发 warning（避免误打扰）
- **关键不变量**：`core/factors.py` 的 chain 函数只接受浮点数；查表逻辑全在 services 层做

**ProjectList query 服务层**（`services/projects.py:list_with_query`）
- `name.ilike(f"%{q}%")` 走 SQLAlchemy 参数化，不是字符串拼接 SQL
- 排序字段白名单 `_SORT_COLUMNS = {created_at, updated_at, name, target_cost}`
- 分页 `offset((page-1)*size).limit(size)`；`size` API 层 clamp 到 [1, 200]

### 前端新增

**5 个新组件**（`web/src/components/`）：

| 组件 | 用途 |
|---|---|
| `AlphaSlider.vue` | dev_and_ops 项目的 alpha_dev 滑块（范围 0.5–1.0, step 0.05, 默认 0.7），实时显示运维占比 = 1−α |
| `FactorTable.vue` | ParamManager 因子 tab 的可编辑表（每个 level 一行 multiplier 输入），emit update:multiplier |
| `FactorDropdown.vue` | Wizard step 5/6 的因子选择 dropdown — 每个 factor 一个 select，option 显示 `level — ×multiplier` |
| `PhaseCfPreview.vue` | Wizard step 3 — 5 个 phase card 横排，每个显示 CF 数值 + 含义提示 |
| `ProjectActionMenu.vue` | ProjectList 行末 ⋯ 菜单：复制 / 审计 / 删除 |

**1 个新 view**：`AuditView.vue`（路由 `/projects/:id/audit`）— 时间线展示 audit_log，cursor 分页 `before_id` 翻页。

**3 个新 api client**（`web/src/api/`）：
- `snapshots.ts` — `snapshotsApi.{list, create, restore, remove}` 走新 envelope `{success, data, error}`
- `audit.ts` — `auditApi.list(projectId, {limit, beforeId})`
- `projects.ts` 扩展 — `projectsApi.query(opts)`（新 envelope + meta）+ `copy(srcId, name)`

**大改 view**：

| View | 改动 |
|---|---|
| `ProjectWizard.vue` | 5 步 → 7 步（基础信息 / 项目类型 / 阶段 / 正反向 / 开发因子 / 运维因子 / 确认）；form 新增 client / evaluator / factors_dev / factors_ops；submit 写进 create payload |
| `ParamManager.vue` | v1.1 的 4 个 stub tab（factors_dev / factors_ops / scale_change / snapshots）全部实装；rate tab 加 ops 列；productivity tab 加 ops 表 |
| `ProjectList.vue` | toolbar：搜索（防抖 250ms）+ 城市/行业/阶段/排序字段 + 升降序；分页（PAGE_SIZE=20）；行末 ⋯ 菜单 |
| `FpEditor.vue` | 上传后 hint 用户用 `/cost`；新 FP `source="claude_draft"` 用浅黄底 + AI 草稿徽标；30s 自动 polling FP 列表（用户也可手动点"立即刷新"） |
| `ResultView.vue` | 反向路径下方加 allocator panel — 用户输入 drafts JSON → 调 `/api/calc/allocate` → 渲染分摊结果 |

> **依赖瘦身**：v2.0 移除 `element-plus`（源码 0 实际使用）。`vendor-element.js` 921 KB / 297 KB gzip → **0**，整体 dist gzipped 约 -85%，build 时间 1.83s → 0.46s。

### Plugin 链路（GAP-A AI 提取 + GAP-C AI 分摊）

| 文件 | 用途 |
|---|---|
| `commands/cost.md` | 主工作流：启动 server + 浏览器开页面；带 `<project_id>` 参数时执行 AI FP 提取流程 |
| `commands/cost-allocate.md` | **新增**：反向项目的 AI 模块分摊向导，配合 ResultView 的 allocator panel |
| `SKILL.md` | NESMA 提取 prompt — 5 类别 + 复杂度判定规则 + UFP 表 + 写入约束（source=claude_draft, replace=false） |

### 调试 v2 新功能

```bash
# 看审计流水（注意：actor 当前永远是 "user"，diff_json 含 sub_path + query）
sqlite3 ~/.claude/projects/cost-estimation/.data/cost.sqlite \
  "SELECT ts, action, target, diff_json FROM audit_log ORDER BY id DESC LIMIT 20;"

# 看快照列表
curl -H "X-Auth-Token: $TOKEN" http://127.0.0.1:8788/api/params/snapshots

# 复算 effective params（无项目作用域）
curl -H "X-Auth-Token: $TOKEN" http://127.0.0.1:8788/api/params/effective | jq .

# 测项目级 factor 生效（factors_dev 设置前后 dev_cost 应该不同）
curl -X PATCH -H "X-Auth-Token: $TOKEN" -H "Content-Type: application/json" \
  "http://127.0.0.1:8788/api/projects/$PID" \
  -d '{"factors_dev":{"app_type":"流程控制","integrity_level":"A_full_lifecycle"}}'
curl -X POST -H "X-Auth-Token: $TOKEN" -H "Content-Type: application/json" \
  "http://127.0.0.1:8788/api/calc/forward" -d "{\"project_id\":\"$PID\"}" | jq .data.cost_dev_yuan
```

### 扩展点

- **加新 audit action**：改 `app/middleware/audit.py:_action_for` 的 if-else 链；新 action 字符串值同步到 `AuditView.vue:ACTION_LABELS` 中文映射
- **加新 factor 维度**：在 `services/factors.py` 的 `_compute_dev_factor`/`_compute_ops_factor` 加新维度，CSBMK json 加对应数据；core/factors.py 的 `dev_factor_chain` / `ops_factor_chain` 签名也要扩
- **加新 ParamManager tab**：`views/ParamManager.vue` 的 `TABS` 数组加项 + 对应 `<section v-else-if="activeTab === 'xxx'">` block
- **支持新查询字段**：`services/projects.py:list_with_query` 加 filter + `_SORT_COLUMNS` 白名单 + `api/projects.py:list_` 加 Query 参数 + `api/projects.ts:ProjectQuery` 类型同步

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
