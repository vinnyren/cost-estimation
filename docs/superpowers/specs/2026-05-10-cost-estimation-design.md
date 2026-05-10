# 软件造价制作系统 · 设计规范

**版本**：v1.0
**日期**：2026-05-10
**状态**：草案
**依据标准**：GB/T 36964 / T/CCUA 005-2024 / GB/T 28827.7-2022 / GB/T 42452-2023
**基准数据**：CSBMK®-202510（2025 年中国软件行业基准数据）

---

## 1. 项目目标与范围

### 1.1 一句话目标

构建一套基于 Claude Code Plugin + Web 服务的"软件造价制作系统"，让用户能：
- **正向**：上传需求文档（功能清单/使用手册/可研/初设报告）→ 得到符合实施规程的造价评估结果
- **反向**：输入目标造价金额 → 反推总功能点 → 自动分摊到具体模块
- 最终输出标准化 Excel 报告，支持一键安装。

### 1.2 范围内（v1）

- 软件**开发**与软件**运维**两类项目（与实施规程 5.3 一致）
- NESMA 估算功能点法为默认（兼容 IFPUG 详细计数）
- 支持 35 个城市人月费率（CSBMK 4.7/4.8）、6 大业务领域生产率（CSBMK 4.1）
- 全量参数可编辑：附录 B 全部 17 张调整因子表 + 规模变更因子 + 工作量分布
- Excel 输出严格遵循实施规程附录 A（FP 计数模板）+ 附录 C（评估报告模板）
- 反向模式默认仅开发（α=1.0），用户可勾选启用运维占比

### 1.3 范围外（v1）

- COSMIC 方法（GB/T 42452）的完整支持（仅保留扩展位）
- 多用户协作、用户系统、远程部署
- 历史版本基准数据（仅内置 CSBMK®-202510，可手动导入其他版本）
- 在线团队协作
- 移动端适配

---

## 2. 关键决策记录（来自 Brainstorming）

| # | 决策 | 选项 | 理由 |
|---|---|---|---|
| 1 | 系统形态 | Claude Code Plugin（Skill + 后端 Web + 浏览器 UI） | Skill 即"安装包"又是"启动器"，浏览器为主交互面 |
| 2 | 双向能力 | Forward + Reverse 双模式切换 | 同时满足"已有需求估算成本"和"已有预算反推 FP" |
| 3 | FP 提取方式 | Claude 读文档生成初稿 → Web 表格用户微调 | 灵活度最高，覆盖结构化与非结构化文档 |
| 4 | FP 方法 | NESMA 估算法默认，IFPUG 兼容 | 符合实施规程附录 A 模板与 CSBMK 生产率口径 |
| 5 | 项目类型 | 开发 + 运维 同时支持 | 与实施规程示例一致，B.1-B.6 与 B.7-B.17 都用 |
| 6 | 参数管理 | 全量可编辑，CSBMK®-202510 为默认 | 用户可精确控制评估口径 |
| 7 | 技术栈 | Python (FastAPI) + Vue 3 + openpyxl | Python 在 Excel/PDF 生态最成熟 |
| 8 | 反向 α | 默认 α=1.0（仅开发），用户主动勾选启用运维占比 | 避免默认引入误导，主动选择更稳健 |
| 9 | 区间模型 | 直接用 PDR 的 P10/P50/P90 | 比 P50±20% 更真实地反映行业生产率分布 |
| 10 | 存储 | SQLite（项目元信息 + FP 清单 + 参数） | 单文件、零配置、并发可靠；JSON 仍用于参数导入/导出 |
| 11 | FP 编辑历史 | 保留前 5 版 | 支持"撤销批量重平衡"，避免无限增长 |

---

## 3. 系统架构

### 3.1 组件拓扑

```
┌────────────────────────────┐
│  Claude Code (host)        │
│  用户输入 /cost            │
└───────────┬────────────────┘
            │ Skill 激活 → start.sh
            ▼
┌────────────────────────────┐         ┌──────────────────────────┐
│ FastAPI 后端 (127.0.0.1:8788)│ <───>  │ SQLite 数据库            │
│  · 项目 / FP / 参数 / 计算  │         │ ~/.claude/projects/      │
│  · Excel 生成 (openpyxl)   │         │   cost-estimation/db/    │
│  · 文档解析 (pdfplumber等) │         │     cost.sqlite          │
└───────────┬────────────────┘         └──────────────────────────┘
            │ open http://127.0.0.1:8788
            ▼
┌────────────────────────────┐
│  Vue 3 SPA · 主交互面      │
│  上传/编辑/计算/导出       │
└───────────┬────────────────┘
            │ 用户点击"AI 辅助提取/分摊"
            │ 通过 SSE 通知 Skill
            ▼
┌────────────────────────────┐
│  Claude (本会话)            │
│  读 uploads/*.{pdf,docx}   │
│  生成 FP 初稿                │
│  调 POST /api/.../bulk      │
└────────────────────────────┘
```

### 3.2 仓库结构（开发态）

```
cost-estimation-plugin/
├── .claude-plugin/marketplace.json
├── plugin.json
├── README.md
├── skills/cost-estimation/
│   ├── SKILL.md
│   ├── doc-extract.md
│   └── reference/
│       ├── nesma-rules.md
│       ├── factor-tables.md
│       └── workflow.md
├── server/
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── alembic/                    # SQLite migrations
│   ├── app/
│   │   ├── main.py
│   │   ├── api/                    # 路由
│   │   ├── core/                   # 算法（forward/reverse/allocator）
│   │   ├── parsers/                # 文档解析
│   │   ├── exporters/excel.py
│   │   ├── data/                   # 内置基准数据 JSON（seed 用）
│   │   ├── db/                     # SQLAlchemy models
│   │   ├── storage/
│   │   └── schemas/                # Pydantic v2
│   └── templates/report-v1.xlsx
├── web/
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── views/
│   │   │   ├── ProjectList.vue
│   │   │   ├── ProjectWizard.vue
│   │   │   ├── FunctionPoints.vue
│   │   │   ├── Parameters.vue
│   │   │   └── Result.vue
│   │   ├── components/
│   │   ├── api/
│   │   ├── stores/
│   │   └── composables/
│   └── dist/
├── scripts/
│   ├── install.sh
│   ├── start.sh
│   └── stop.sh
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

### 3.3 安装后布局

```
~/.claude/plugins/data/cost-estimation/   # Plugin 代码
├── skills/
├── server/
│   └── .venv/                            # 安装时生成
├── web/dist/
└── scripts/

~/.claude/projects/cost-estimation/        # 用户数据
├── db/
│   └── cost.sqlite                       # 全部业务数据（项目、FP、参数、结果）
├── uploads/
│   └── <project-id>/                     # 用户上传的原始文件
└── exports/
    └── <project-id>/
        └── 评估报告_v1.xlsx
```

---

## 4. 数据模型（SQLite Schema）

### 4.1 主表

```sql
-- 项目元信息
CREATE TABLE projects (
  id              TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL,
  project_type    TEXT NOT NULL,         -- dev_only | ops_only | dev_and_ops
  phase           TEXT NOT NULL,         -- budget | bidding | planning | change | settled
  city            TEXT NOT NULL,
  industry        TEXT NOT NULL,
  client          TEXT,
  evaluator       TEXT,
  mode            TEXT NOT NULL,         -- forward | reverse
  target_cost     REAL,                  -- 仅 reverse
  other_cost      REAL DEFAULT 0,
  include_ops     INTEGER DEFAULT 0,     -- 反向时是否启用运维
  alpha_dev       REAL DEFAULT 1.0,
  fp_method       TEXT DEFAULT 'nesma_estimated',
  basis_data_ver  TEXT NOT NULL          -- e.g. "CSBMK®-202510"
);

-- FP 清单（带历史）
CREATE TABLE function_points (
  id              TEXT PRIMARY KEY,
  project_id      TEXT NOT NULL REFERENCES projects(id),
  version         INTEGER NOT NULL,        -- 当前版本
  subsystem       TEXT,
  l1_module       TEXT,
  l2_module       TEXT,
  description     TEXT,
  name            TEXT,
  category        TEXT NOT NULL,           -- EI | EO | EQ | ILF | EIF
  complexity      TEXT NOT NULL,           -- low | average | high
  ufp             REAL NOT NULL,
  reuse_level     TEXT,
  modify_type     TEXT,                    -- new | modify | delete
  us              REAL NOT NULL,
  source          TEXT,                    -- claude_draft | manual | imported
  locked          INTEGER DEFAULT 0,
  notes           TEXT,
  ord             INTEGER                  -- 排序
);

-- FP 历史快照（保留前 5 版）
CREATE TABLE fp_snapshots (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id      TEXT NOT NULL REFERENCES projects(id),
  version         INTEGER NOT NULL,
  snapshot_at     TEXT NOT NULL,
  snapshot_json   TEXT NOT NULL,           -- 整个 FP 清单序列化
  reason          TEXT                     -- 'auto_save' | 'before_ai_alloc' | ...
);
-- 触发器：超过 5 版自动删除最早

-- 全局参数（CSBMK®-202510 + 用户全局修改）
CREATE TABLE params_global (
  key             TEXT PRIMARY KEY,        -- 点路径，e.g. 'productivity.dev.电子政务.P50'
  value           TEXT NOT NULL,           -- JSON 编码
  basis_version   TEXT NOT NULL,
  modified        INTEGER DEFAULT 0,       -- 是否被用户改过
  updated_at      TEXT
);

-- 项目级参数覆盖
CREATE TABLE params_override (
  project_id      TEXT NOT NULL REFERENCES projects(id),
  key             TEXT NOT NULL,
  value           TEXT NOT NULL,
  reason          TEXT,
  updated_at      TEXT,
  PRIMARY KEY (project_id, key)
);

-- 参数快照（用户重置/导入前）
CREATE TABLE params_snapshots (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  taken_at        TEXT NOT NULL,
  reason          TEXT,
  payload_json    TEXT NOT NULL
);

-- 计算结果（不可变快照）
CREATE TABLE results (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id      TEXT NOT NULL REFERENCES projects(id),
  computed_at     TEXT NOT NULL,
  mode            TEXT NOT NULL,           -- forward | reverse
  fp_version      INTEGER NOT NULL,
  params_hash     TEXT NOT NULL,
  payload_json    TEXT NOT NULL,
  is_stale        INTEGER DEFAULT 0
);

-- 上传文件清单
CREATE TABLE uploads (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id      TEXT NOT NULL REFERENCES projects(id),
  filename        TEXT NOT NULL,
  size            INTEGER,
  uploaded_at     TEXT NOT NULL,
  filetype        TEXT,                    -- pdf | docx | xlsx | md
  parsed_text     TEXT                     -- 缓存的纯文本提取结果
);
```

### 4.2 参数解析顺序

计算引擎读取参数时按以下顺序合并：

```
params_global (含 CSBMK®-202510 默认值 + 用户全局修改)
  →  params_override (本项目专属覆盖)
  →  projects.{city, industry, phase, ...} (项目本身设定)
  =  effective parameters
```

### 4.3 一致性约束

- `results.params_hash` = SHA256(effective_params + functions_version)；参数或 FP 变更后自动设置 `is_stale=1`
- FP 编辑：每次保存后写入新版本号，并将快照写入 `fp_snapshots`；超过 5 版触发器删除最旧
- 项目目录用文件锁（操作 SQLite 时 SQLite 自身 WAL 模式即可）

---

## 5. 核心算法

### 5.1 正向计算（Forward）

输入：FP 清单 + 项目元信息 + 调整因子取值
输出：三档结果（PDR P10/P50/P90 对应）

```
步骤：
  1. US = Σ FP[i].us                          # 未调整规模
  2. CF = phase → cf_table 查值                # 1.39/1.21/1.10/1.00
  3. S  = US × CF                              # 调整后规模
  4. 对 PDR ∈ {P10, P50, P90}:
       UE = PDR × S                           # 未调整工作量（人时）
       AE = UE × Π(因子)                      # 调整后工作量
       PM = AE / 174                           # 人月数
       Cost = PM × F_city                     # 成本（元）
  5. 输出 {dev: {P10, P50, P90}, ops: {P10, P50, P90}, total}
```

**因子组合**：

- 开发：`F = app_type × non_func × integrity × dev_lang × dev_team`
  - 非功能因子：`= (分布式 + 性能 + 可靠性 + 多重站点) × 0.025 + 1`，每项 ∈ {-1, 0, 1}
- 运维：`F = 业务重要性 × 网络安全 × 支持方式 × 更新频率 × 响应时效 × 完整性 × 采用技术 × 团队 × 部署方式 × 用户规模 × 系统关联性`

### 5.2 反向反推（Reverse）

输入：目标金额 T、其他费用 O、α（开发占比）、城市、行业、阶段、调整因子取值
输出：US、S 三档（对应 PDR 三档）

```
步骤：
  1. 可用预算 = T - O
  2. 若 include_ops:
       Budget_dev = (T - O) × α
       Budget_ops = (T - O) × (1 - α)
     否则:
       Budget_dev = T - O；Budget_ops = 0
  3. 各自反算：
       PM   = Budget / F_city
       AE   = PM × 174
       UE   = AE / Π(调整因子)
  4. 反求规模（对应 PDR 三档）：
       S_紧 = UE / PDR_P10                   # 高生产率 = 小规模
       S_中 = UE / PDR_P50
       S_松 = UE / PDR_P90
  5. US = S / CF
  6. 检查：若已有 FP 草稿合计在 [S_紧, S_松] 内，预算合理；否则提示
```

### 5.3 模块分摊（Allocator）

输入：目标 S（中值，建议）+ 文档解析得到的模块树 + 可选 Claude 初稿权重
输出：完整 FP 清单（每条带类别、复杂度、UFP）

```
步骤：
  1. 权重来源（按优先级）：
     A. Claude 初稿 UFP 数列 w_i
     B. 用户在 Web UI 的自定义权重
     C. 等权 + 类别默认 UFP

  2. 归一与分配：
       UFP_i = round(S_target × w_i / Σw_j, 2)

  3. 类别分布约束：
     ILF≈14% / EI≈50% / EO≈7% / EQ≈29% / EIF≈0%（参考实施规程示例）
     允许 ±5% 漂移；超出则在保持总和不变的前提下重平衡

  4. 取整：UFP 落到 NESMA 估算合法值（详细法可走完整 IFPUG 表）

  5. 双向一致性校验：
     重新走一遍 forward(分摊后 FP) → 计算 cost
     若 |cost - target| / target > 1%，提示用户

  6. 锁定的 FP（locked=1）不参与重平衡
```

### 5.4 黄金测试

实施规程附录 D 完整算例作为黄金测试：

```
输入：
  - 政务服务平台 6 模块、275 FP
  - 阶段=招投标(CF=1.21)、城市=北京、行业=电子政务
  - 开发因子=1.0、运维因子=1.18
  - 其他费用=2.5 万元

期望输出（CSBMK®-202210 数据下）：
  - 调整后 S = 332.75 FP
  - 总费用中值 = 48.92 万元
  - 总费用范围 = 39.65 - 58.19 万元
```

CSBMK 数据每年更新，因此测试也需配备 202210 历史数据用于精确复现。

---

## 6. Web UI 与用户流程

### 6.1 路径 A · Forward

```
新建项目(模式=Forward)
  → 元信息(城市/行业/阶段)
  → 上传文档
  → "AI 辅助提取" → Claude 读 → 写回 FP 初稿
  → FP 表格微调
  → 调整因子设置
  → 计算 → 三档结果
  → 下载 Excel
```

### 6.2 路径 B · Reverse

```
新建项目(模式=Reverse)
  → 元信息 + 目标金额 + α 设置
  → 调整因子设置
  → 反算 → 三档总 FP
  → 上传文档(可选)
  → "AI 辅助分摊" → Claude 拆到模块
  → FP 表格微调
  → 自动校验"反算回去 ≈ 目标"
  → 下载 Excel
```

### 6.3 主屏清单

| 屏 | 路由 | 关键交互 |
|---|---|---|
| 项目列表 | `/` | 新建/打开/导入备份；显示模式徽章、当前总 FP/总费用 |
| 项目向导 | `/projects/new` | 5 步进度条；模式与元信息选择 |
| FP 编辑 | `/projects/{id}/functions` | 左侧模块树 + 右侧 vxe-table；AI 提取/分摊按钮；批量操作；类别分布统计 |
| 参数管理 | `/projects/{id}/parameters` | 6 Tab（费率/生产率/开发因子/运维因子/规模变更/快照）；覆盖项黄底高亮 |
| 结果页 | `/projects/{id}/result` | Forward：三档金额卡片；Reverse：三档 FP 卡片 + 反算输入区；底部下载按钮 |

### 6.4 关键 UI 决策

- **vxe-table** 处理大型 FP 表（百行以上）的批量编辑、虚拟滚动、列排序
- **Element Plus** 提供 Form/Tab/Drawer/Notification 等基础组件
- **Pinia** 管理项目元信息、参数覆盖、计算结果三个 store
- **路由守卫**：未保存改动离开页面时弹确认；参数变更后旧结果显示 stale 标识

---

## 7. Excel 输出

### 7.1 模板结构（report-v1.xlsx，7 Sheets）

| Sheet | 内容 | 来源 |
|---|---|---|
| 1. 封面声明 | 评估机构、报告声明（不变文本）、生成日期 | 实施规程附录 C |
| 2. 评估结果摘要 | 7 项评估结果三档汇总表 | 附录 C 摘要表 |
| 3. 评估报告书 | 项目概述 / 评估目的 / 依据 / 方法（Claude 在生成 Excel 前预填） | 附录 C |
| 4. 调整因子表 | 17+ 个因子的取值与说明 | 附录 C 因子表 |
| 5. 功能点计数表 | 完整 FP 清单（子系统/一级模块/二级模块/描述/类别/UFP/重用/修改/US） | 附录 A 模板 |
| 6. 详细计算过程 | US→CF→PDR→AE→Cost 的逐步展开 | 附录 D 风格 |
| 7. 参数附录 | 本次计算用到的全部参数值与版本号、来源 | 自有 |

### 7.2 生成方式

```python
# server/app/exporters/excel.py
wb = openpyxl.load_workbook('templates/report-v1.xlsx')

# 摘要 Sheet：按命名区域填值（保留模板格式）
wb['评估结果摘要']['B5'] = result.scale.adjusted
wb['评估结果摘要']['C8'] = result.cost_yuan.total.P50

# FP 计数表：批量写入行（保留表格样式与边框）
ws = wb['功能点计数表']
for i, fp in enumerate(functions, start=template_first_row):
    ws.cell(i, 1, i - template_first_row + 1)
    ws.cell(i, 2, fp.subsystem)
    # ... 其他列

wb.save(output_path)
```

模板使用命名区域（Defined Names）而非硬编码单元格地址，便于模板演进。

---

## 8. Skill 与一键安装

### 8.1 Plugin 元信息

```json
// .claude-plugin/marketplace.json
{
  "name": "cost-estimation",
  "description": "基于 GB/T 36964 / T/CCUA 005-2024 / CSBMK®-202510 的软件造价制作系统",
  "version": "1.0.0",
  "skills": [
    {
      "path": "skills/cost-estimation",
      "description": "软件造价评估 · NESMA 估算 · 双向（FP↔成本）"
    }
  ],
  "commands": [
    { "name": "cost", "description": "启动造价评估 Web 服务" },
    { "name": "cost-stop", "description": "停止后端服务" }
  ],
  "post_install": "scripts/install.sh"
}
```

### 8.2 用户安装命令

```bash
# 在 Claude Code 内
/plugin install github.com/your-org/cost-estimation
```

### 8.3 install.sh 主要步骤

1. 创建 `~/.claude/projects/cost-estimation/{db,uploads,exports}` 目录
2. 在 `server/` 下创建 Python venv（python3 -m venv .venv）
3. `pip install -r requirements.txt`（fastapi/uvicorn/openpyxl/pdfplumber/python-docx/sqlalchemy/pydantic）
4. `python -m app.bootstrap` 初始化 SQLite + 写入 CSBMK®-202510 默认参数

### 8.4 start.sh 启动逻辑

1. 检查 8788 端口是否已占用；占用则提示并退出
2. `nohup uvicorn app.main:app --host 127.0.0.1 --port 8788 &`
3. 轮询 `/health` 等待就绪
4. `open http://127.0.0.1:8788/`

### 8.5 SKILL.md 触发与编排

```markdown
---
name: cost-estimation
description: Use when the user wants to do software cost estimation per Chinese GB/T 36964 standards, including forward calculation (scope → cost) or reverse derivation (target cost → function points). Triggers on phrases: "造价评估" / "功能点估算" / "软件成本" / "/cost".
---

## 使用流程

1. 用户调用 `/cost` 时运行 `scripts/start.sh` 启动后端
2. 浏览器自动打开 http://localhost:8788/
3. 用户在 FP 编辑页点 "AI 辅助提取" 时本 Skill 接管：
   - 读取项目目录下 uploads/*.{pdf,docx,xlsx}
   - 按 NESMA 估算法生成 FP 初稿（参考 reference/nesma-rules.md）
   - 调用 POST /api/projects/{id}/functions/bulk 写回
4. 反向模式："AI 辅助分摊" 调 POST /api/calc/allocate

## 不要做的事

- 不在会话里逐个询问 FP 项（让用户在 Web 表格里编辑）
- 不修改 params_global 表（用 params_override）
- 不直接生成 Excel；调 GET /api/reports/excel/{id}
```

---

## 9. API 设计（FastAPI）

### 9.1 路由清单

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| GET | `/api/projects` | 列出项目 |
| POST | `/api/projects` | 创建项目 |
| GET | `/api/projects/{id}` | 项目详情 |
| PATCH | `/api/projects/{id}` | 修改元信息 |
| DELETE | `/api/projects/{id}` | 删除项目 |
| POST | `/api/projects/{id}/uploads` | 上传文档（multipart） |
| GET | `/api/projects/{id}/functions` | 获取 FP 清单 |
| PATCH | `/api/projects/{id}/functions/{fp_id}` | 编辑单条 FP |
| POST | `/api/projects/{id}/functions/bulk` | 批量写入 FP（用于 AI 初稿与分摊回写） |
| POST | `/api/projects/{id}/functions/restore?version=N` | 回滚到第 N 版 |
| GET | `/api/projects/{id}/params/effective` | 当前生效参数 |
| GET | `/api/params/global` | 全局参数 |
| PATCH | `/api/params/global` | 修改全局参数 |
| POST | `/api/params/global/reset` | 重置为 CSBMK 默认 |
| PATCH | `/api/projects/{id}/params/override` | 项目级参数覆盖 |
| POST | `/api/calc/forward` | 正向计算 |
| POST | `/api/calc/reverse` | 反向反推 |
| POST | `/api/calc/allocate` | 模块分摊 |
| GET | `/api/projects/{id}/results` | 历史结果 |
| GET | `/api/reports/excel/{project_id}` | 下载 Excel |

### 9.2 错误响应格式

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_PARAM",
    "message": "城市 'xxxxx' 不在 CSBMK 35 城市列表中",
    "details": { "field": "city" }
  }
}
```

成功统一：

```json
{ "ok": true, "data": { ... }, "meta": { ... } }
```

---

## 10. 错误处理与边界条件

| 场景 | 处理 |
|---|---|
| 上传文件 > 50MB | 拒绝，返回 413 |
| Claude 提取的 FP 项数 = 0 | UI 提示"未识别到功能项，请检查文档质量或手动添加" |
| 反向计算预算 ≤ 0 | 返回 INVALID_PARAM "目标金额必须大于其他费用" |
| 城市/行业不在 CSBMK | 接受为自定义键，但提示"非内置参数，请在参数库手动维护" |
| 8788 端口被占用 | start.sh 自动尝试 8789…8800；写入实际端口到 `.port` 文件 |
| 参数被改后未重新计算 | 结果页顶部显示橙色"已过期"横条，提供"重新计算"按钮 |
| FP 总数为 0 时尝试计算 | 返回 INVALID_STATE "FP 清单为空" |
| Excel 导出时 FP 项 > 5000 | 走流式写入；超过 10000 项警告并询问是否继续 |
| SQLite 库文件损坏 | 启动时校验，损坏则备份原文件并从 seed JSON 重建 |

---

## 11. 测试策略

### 11.1 单元测试（pytest，目标覆盖 80%+）

- `test_forward.py`：附录 D 完整算例黄金测试 + 边界条件
- `test_reverse.py`：α=1.0 / α=0.917 双场景；边界（目标=0、α 越界）
- `test_allocator.py`：分摊后回算容差 ≤1%；锁定项行为
- `test_factors.py`：开发/运维所有因子组合；非功能因子边界
- `test_params_override.py`：覆盖合并、回滚、快照
- `test_db_models.py`：SQLite 模型与触发器（5 版限制）

### 11.2 集成测试（pytest + httpx.AsyncClient）

- 项目 CRUD 全流程
- 文档上传 → AI 提取 → FP 写回（mock Claude 响应）
- forward + reverse 计算并校验 results.params_hash
- Excel 下载用 openpyxl 重读校验关键单元格
- 参数修改触发 is_stale=1

### 11.3 前端 + E2E

- Vue 单元测试（vitest）：FP 表格组件、Pinia store、参数覆盖热更新
- Playwright E2E：完整 5 步向导、Reverse 路径、跨城市切换

### 11.4 黄金测试基准

`tests/golden/appendix-d.json` 内置实施规程附录 D 输入 + 期望输出。任何参数表/算法重构必须保持此测试通过。

---

## 12. 实施阶段

| 阶段 | 主要交付物 | 估时 |
|---|---|---|
| Phase 1 · 后端骨架 | FastAPI + SQLite + 项目 CRUD + 参数管理 | 4 天 |
| Phase 2 · 计算引擎 | forward / reverse / allocator + 黄金测试 | 5 天 |
| Phase 3 · 文档解析 | PDF/Word/Excel 解析 + Skill SKILL.md | 3 天 |
| Phase 4 · Excel 导出 | openpyxl 模板 + 7 Sheet 渲染 | 3 天 |
| Phase 5 · 前端 | Vue 5 屏 + vxe-table + Pinia | 7 天 |
| Phase 6 · 打包安装 | Plugin 元信息 + install.sh / start.sh | 2 天 |
| Phase 7 · 测试与文档 | 80% 覆盖 + E2E + 用户文档 | 4 天 |

总计约 28 个工作日。

---

## 13. 风险与缓解

| 风险 | 等级 | 缓解 |
|---|---|---|
| Claude 提取 FP 准确率不稳定 | H | 严格的 reference/nesma-rules.md 提示词；UI 让用户能高效复核；初稿打 source 标记便于审计 |
| 实施规程未来版本变化 | M | 参数表与算法解耦；版本号显式记录在结果中；提供 "导入新版 CSBMK" 入口 |
| openpyxl 模板兼容性 | M | 模板版本化；Excel 测试用 openpyxl 自身重读校验，不依赖 Office |
| 端口占用导致启动失败 | L | 自动端口探测 + `.port` 文件 + UI 显示当前端口 |
| 多用户并发写入 | L | v1 仅本地单用户；SQLite WAL 模式可应对偶发并发；远程多人留 v2 |

---

## 14. 验收标准

- [ ] 一键安装：`/plugin install` → 自动 venv + 依赖 + SQLite seed
- [ ] `/cost` 唤起 → 浏览器自动打开 → 可以走完 5 步向导导出 Excel
- [ ] 黄金测试（附录 D 算例）：输出 = 48.92 万元 ±0.01（中值）
- [ ] 反向模式：目标 50 万 → 三档 FP，反算回去 ≤1% 误差
- [ ] 参数全量可改 + 重置 + 快照回滚
- [ ] 测试覆盖 ≥ 80%
- [ ] Excel 用 Office/WPS 正常打开，格式无错乱

---

## 15. 后续扩展（v2+）

- COSMIC 方法（GB/T 42452）完整支持
- 多用户 + 角色权限 + 远程部署
- 历史 CSBMK 版本切换
- 评估报告 Word 导出
- 移动端响应式
- 与 Linear/Jira 集成（功能项导入导出）
