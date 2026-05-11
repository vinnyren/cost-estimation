# 软件造价制作系统

基于 GB/T 36964 / T/CCUA 005-2024 / GB/T 28827.7-2022 / GB/T 42452-2023 与 CSBMK®-202510 数据集的软件造价评估工具，作为 Claude Code Plugin 发布。

## 功能

- ✅ **正向模式**（功能点 → 成本）：上传需求文档 → AI 提取 FP → 三档成本估算
- ✅ **反向模式**（目标成本 → 功能点）：输入预算 → 反推三档 FP → AI 分摊到模块
- ✅ **NESMA 估算法**（默认）：EI/EO/EQ/ILF/EIF 5 类、低中高复杂度
- ✅ **6 行业 + 37 城**生产率与费率（CSBMK®-202510 内置）
- ✅ **17+ 调整因子全部可配**：开发因子 5 项 + 运维因子 11 项 + CF 阶段因子（v2.0 ParamManager 实装）
- ✅ **AI 提取功能点**（v2.0）：`/cost <project_id>` 让 Claude Code 读上传文档生成 NESMA FP 草稿
- ✅ **AI 模块分摊**（v2.0）：`/cost-allocate <project_id>` 反向模式三档 FP → 模块清单
- ✅ **7 步 Wizard 创建项目**（v2.0）：客户/评估方 + 项目类型 + 阶段 + 因子选择 + 实时 CF 预览
- ✅ **参数快照 + 项目复制 + 审计日志**（v2.0）
- ✅ **Excel 报告**：7 Sheet 模板（封面 / 摘要 / 报告书 / 调整因子 / FP 表 / 详细计算 / 参数附录）
- ✅ **本地隔离**：只绑 127.0.0.1，token + Origin + CORS 三层防护

## v2.0 新功能（2026-05-11）

### 11 项 v1.1 后审计 gap 全部闭环

- ✅ **AI 提取功能点**（GAP-A）：在 Claude Code 终端运行 `/cost <project_id>`，AI 读取上传文档自动生成 NESMA FP 草稿
- ✅ **AI 模块分摊**（GAP-C）：反向模式下 `/cost-allocate <project_id>` 让 AI 把三档 FP 拆成模块清单
- ✅ **17+ 调整因子全部可配**（GAP-B）：ParamManager 4 个 v2 stub tab 实装；Wizard 第 5/6 步用 dropdown 选因子级别，实时显示链式相乘
- ✅ **运维费率 / 生产率**（GAP-D）：城市费率表新增 ops 列；生产率 tab 新增运维行业表
- ✅ **alpha_dev / include_ops**（GAP-E）：dev_and_ops 项目类型显式滑块 + 联动开关
- ✅ **客户 / 评估方填写**（GAP-G）：Wizard 第 1 步可选字段，写入 Excel 报告封面
- ✅ **项目列表搜索 / 筛选 / 排序 / 分页**（GAP-F）：toolbar 实时搜索，5 个筛选维度
- ✅ **参数快照 + restore**（GAP-H）：ParamManager 快照 tab 可创建 / 恢复 / 删除
- ✅ **项目复制**（GAP-I）：行 ⋯ 菜单一键复制项目（含 FP + 参数 override）
- ✅ **项目审计日志**（GAP-J）：所有 mutating 操作自动记录，AuditView 可查
- ✅ **阶段 CF 实时预览**（GAP-K）：Wizard 第 3 步显示选定阶段的 CF 调整因子值

### 数据迁移

v1.1 老项目自动兼容：
- `factors_dev_json` / `factors_ops_json` 为 NULL → calc 用 1.0 + Result.warning_messages 提示
- 已有参数 / FP / 上传 不受影响
- 跑 `cd server && alembic upgrade head` 应用 3 个新 migration（factors 列、param_snapshots 表、audit_log 表）

### 新 API endpoint

- `POST /api/projects/{id}/copy` — 项目复制
- `GET /api/projects/{id}/audit` — 项目审计日志（cursor 分页）
- `GET /api/params/snapshots` / `POST` / `POST /{id}/restore` / `DELETE /{id}` — 参数快照 CRUD
- `GET /api/projects` 升级查询参数 — q / city / industry / phase / mode / sort / order / page / size
- `GET /api/params/effective` — 全局 effective 视图（无项目作用域）

### 新前端 view

- `/projects/:id/audit` — 项目审计时间线

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
├── .claude-plugin/         # Plugin 元信息（marketplace.json + plugin.json）
├── commands/               # slash 命令（setup / cost / cost-stop）
├── reference/              # NESMA 规则 + CSBMK 说明
├── server/                 # FastAPI 后端 + 计算引擎
│   ├── app/
│   │   ├── core/           # 算法核心（forward / reverse / allocator）
│   │   ├── api/            # REST 路由
│   │   ├── parsers/        # PDF / Word / Excel 解析
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

## 覆盖率验证（v2.1+）

项目维护 `coverage-baseline.json` 防止覆盖率退化。本地验证：

```bash
# 跑全套测试 + 与 baseline 比对（>0.5% 退化时退出 1）
./scripts/check-coverage.sh

# 覆盖率上升时锁定新 baseline
./scripts/update-coverage-baseline.sh
```

可选 pre-commit hook（自决）：

```bash
ln -sf ../../scripts/check-coverage.sh .git/hooks/pre-commit
```

测试基线（v2.1）：

| 项 | 数量 | line coverage |
|---|---:|---:|
| Backend pytest | 173 | 91.9% |
| Frontend vitest | 220 | 97.8% |
| Playwright e2e | 13 | n/a |

## v2.2 — 设计 import 全屏重做

v2.2 把 claude.ai/design import 的 6 屏以**像素级复刻**落到前端，并补齐后端 4 个 endpoint。

### 前端

- 暗色 sidebar + topbar 双区布局 + ⌘K 命令面板
- ProjectList KPI cards + 城市/行业/阶段 filter + table/card 视图切换
- ResultView 9 步 Pipeline 详解 + 4 段 CostBar + 合规说明卡
- AuditView 时间轴重做（替换 v2.0 的表格视图）
- FpEditor AI 提取模态对话框（CLI 触发 + polling 进度）
- 全局参数库 `/params/global` + 报告中心 `/reports` 入口

### 后端

- `GET /api/projects/stats` — KPI 汇总（counts + 本月聚合）
- forward calc 返回 `trace`（9 步详解）+ `composition`（4 段拆分）
- `/api/ai-tasks` CRUD endpoints — AI 任务状态轮询（plugin 接入留 v2.3）

### 新表

- `ai_tasks`（alembic migration 自动应用）

### 升级（v2.1 → v2.2）

```bash
git pull && cd server && .venv/bin/alembic upgrade head
```

### 设计 token 变化

v2.2 全套换 design import 自带 token（详见 `web/src/styles/tokens.css`）：
- 字号基线 13px（v1.x 是 14px）
- 配色 `--accent: #1E5EFF`（v1.x 是 `#165DFF`）
- 字体 Noto Sans SC + JetBrains Mono
- Sidebar 深色 `#0F1626`

Legacy `--color-*` token 保留为 alias，避免破坏旧组件。

### v2.2 测试基线

| 项 | 数量 |
|---|---:|
| pytest | 185 |
| vitest | 221 |
| playwright e2e | 21 |
| backend coverage | 92.27%（见 coverage-baseline.json） |
| frontend coverage | 95.88%（见 coverage-baseline.json） |

## 标准合规

- GB/T 36964-2018 软件工程 软件开发成本度量规范
- T/CCUA 005-2024 软件研发成本度量规范实施指南
- GB/T 28827.7-2022 信息技术服务 运行维护 第 7 部分：成本度量规范
- GB/T 42452-2023 软件工程 软件开发成本度量规范 应用指南
- CSBMK®-202510 中国软件行业基准数据 2025 年 10 月版

## License

MIT
