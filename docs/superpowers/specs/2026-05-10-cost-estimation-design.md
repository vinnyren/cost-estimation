# 软件造价制作系统 · 设计规范

**版本**：v1.1（基于 /autoplan 评审反馈修订）
**日期**：2026-05-10
**状态**：已评审，待实施
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
├── commands/                        # Plugin slash commands
│   ├── setup.md                     # /cost-estimation:setup
│   ├── cost.md                      # /cost
│   └── cost-stop.md                 # /cost-stop
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
- FP 编辑：每次保存后写入新版本号，并将快照写入 `fp_snapshots`
- **fp_snapshots 触发器（按 project_id 分组保留前 5 版）**：

  ```sql
  CREATE TRIGGER trim_fp_snapshots AFTER INSERT ON fp_snapshots
  BEGIN
    DELETE FROM fp_snapshots
    WHERE project_id = NEW.project_id
      AND id NOT IN (
        SELECT id FROM fp_snapshots
        WHERE project_id = NEW.project_id
        ORDER BY id DESC LIMIT 5
      );
  END;
  CREATE INDEX idx_fp_snapshots_project ON fp_snapshots(project_id, id);
  ```

- **并发**：SQLite WAL 模式 + `busy_timeout=5000`；不再用文件锁。前端走乐观锁（携带 `fp_version`，409 冲突时刷新）
- **共享计算上下文**：`server/core/context.py::EvaluationContext` 集中管理 effective params，forward/reverse/allocator 全部从 context 派生（纯函数，便于黄金测试与 hypothesis 性质测试）

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
输出：US、S 三档（对应 PDR 三档"乐观/中位/保守预算口径"）

**业务语义说明（CRITICAL，避免误读）**：

PDR 是"行业生产率分布"，不是"团队生产率"。三档对应**预算口径**而非团队效率：

- **乐观（PDR P10 — 行业最高效率）**：在乐观假设下（团队配合最佳/技术最熟悉/无返工），相同预算能买到的最大功能规模。**Boundary case**，作敏感度上界。
- **中位（PDR P50 — 行业中位）**：基于行业基准多数项目能达到的水平。**推荐值**，报告默认呈现此档。
- **保守（PDR P90 — 行业较低效率）**：考虑各种不确定性（需求蔓延/技术债/沟通损耗），相同预算能保证完成的最小功能规模。**Boundary case**，作敏感度下界。

**关键提示**：直接拿"乐观档 FP 数"承诺给客户存在合规与商业风险（团队不一定达到 P10）。报告必须呈现三档 + 强调 P50 推荐 + 标注"基于 CSBMK®-202510 行业分布"。

```
步骤：
  1. 可用预算 = T - O
  2. 若 include_ops（默认 false，α 默认 1.0）:
       Budget_dev = (T - O) × α
       Budget_ops = (T - O) × (1 - α)
     否则:
       Budget_dev = T - O；Budget_ops = 0
  3. 各自反算：
       PM   = Budget / F_city
       AE   = PM × 174
       UE   = AE / Π(调整因子)
  4. 反求规模（按 PDR 三档,对应预算口径）：
       S_乐观 = UE / PDR_P10        # 乐观口径：可买功能规模上界
       S_中位 = UE / PDR_P50        # 推荐：报告呈现此档
       S_保守 = UE / PDR_P90        # 保守口径：可买功能规模下界
  5. US = S / CF
  6. 检查：若已有 FP 草稿合计在 [S_保守, S_乐观] 内，预算合理；否则提示
  7. UI 与 Excel 报告必须：
     a) 默认推荐 S_中位
     b) 标注"乐观/保守为敏感度边界，非承诺值"
     c) 反向模式输出加水印"基于目标金额倒推"
```

### 5.3 模块分摊（Allocator）

输入：目标 S（默认 S_中位）+ 文档解析得到的模块树 + 可选 Claude 初稿权重
输出：完整 FP 清单（每条带类别、复杂度、UFP）

**两段计算（避免锁定项与 1% 容差冲突）**：

```
步骤：
  1. 权重来源（按优先级）：
     A. Claude 初稿 UFP 数列 w_i
     B. 用户在 Web UI 的自定义权重
     C. 等权 + 类别默认 UFP

  2. 锁定项隔离（先计算）：
     S_locked  = Σ(locked FP[i].us)         # 已锁定项规模合计
     S_free    = S_target - S_locked × CF    # 留给未锁定项的规模
     若 S_free ≤ 0，拒绝并提示"锁定项已超目标，请解锁后重试"

  3. 未锁定项归一与分配（仅在 S_free 上分摊）：
       UFP_i = round(S_free × w_i / Σ(unlocked w_j), 2)

  4. 类别分布约束（仅作用于未锁定项）：
     ILF≈14% / EI≈50% / EO≈7% / EQ≈29% / EIF≈0%（参考实施规程示例）
     允许 ±5% 漂移；超出则在保持未锁定总和不变的前提下重平衡

  5. 取整：UFP 落到 NESMA 估算合法值（详细法可走完整 IFPUG 表）

  6. 双向一致性校验：
     重新走一遍 forward(分摊后 FP, 含锁定项) → 计算 S_actual
     若 |S_actual - S_target| / S_target > 1%（仅检查未锁定误差），提示用户

  7. 反向模式专属：所有 source=allocator 的 FP 项必须打上 audit_tag=budget_derived
     在 Excel 报告与 UI 中显示"预算倒推"水印；与人工/AI 项做视觉区分
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

### 6.4 状态矩阵（每屏 5 态）

每个主屏必须实现以下 5 种状态。`-` 代表不适用。

| 屏 | Loading | Empty | Error | Partial | Stale |
|---|---|---|---|---|---|
| 项目列表 | skeleton 卡片 ×3 | 中央插画 + "新建第一个项目" CTA | 顶部红色 banner + 重试按钮 | 部分加载完显示 + "..."占位 | - |
| 项目向导 | 步条置灰 | 表单空表态默认填示例 | 字段红色边框 + 错误文案 | - | - |
| FP 编辑 | skeleton 行 ×8 | 中央 hero CTA "上传文档让 AI 写第一稿" | banner + 错误详情可展开 | AI 提取部分行已写入则显示进度（12/87）+ 取消 | 顶部黄条 "参数已变，重新计算" + 按钮 |
| 参数管理 | skeleton tab 内容 | "参数库为空，导入 CSBMK®-202510" | 字段级错误提示 + 字段恢复默认 | - | - |
| 结果页 | spinner + "计算中…" | "请先完成 FP 编辑" + 跳回链接 | 红色 banner + "查看错误详情" | 部分计算完显示已知值 + "..."占位 | 顶部黄条 + "重新计算"按钮 |

**通用规则：**
- Loading 超过 3 秒显示进度条；超过 10 秒显示"耐心等待"插画
- Error banner 带 problem + cause + 建议 fix（详见 §10）
- 长任务（AI 提取、Excel 导出）必须有取消按钮
- 网络断开时全局显示 offline 提示条

### 6.5 可访问性基线（WCAG 2.1 AA）

- **键盘导航**：所有交互元素支持 Tab/Enter/Esc；FP 表格支持方向键移动焦点
- **ARIA 标签**：所有 icon button 必带 `aria-label`；动态内容用 `aria-live="polite"`
- **颜色对比**：文本/背景对比度 ≥ 4.5:1；非文本（图标/边框）≥ 3:1
- **覆盖项视觉**（取代"黄底高亮"）：浅琥珀底 `oklch(96% 0.08 95)` + 左侧 3px 实线 `oklch(70% 0.15 70)` + 行尾"自定义"徽章
- **触摸目标**：最小 44×44 px（移动端考虑）
- **Excel 输出**：Sheet 命名规范、表头 row 标记 `<table:header>`、关键单元格 alt text

### 6.6 组件契约（避免 4 程序员 4 版）

| 组件 | 位置 | 默认状态 | 关键交互 |
|---|---|---|---|
| AI 辅助提取按钮 | FP 编辑屏工具栏第一项 | 空表时为屏中央 hero CTA；有数据时降级为 primary 工具栏按钮 | Loading 期间替换为进度条 + 取消按钮 |
| 三档结果卡片 | 结果页顶部 | **横排 3 张，P50 中间居中、加 "推荐" 徽章** | hover 显示详细计算过程；点击查看分项明细 |
| 模块树 | FP 编辑屏左侧 240px | 默认仅展开一级 | 支持折叠/展开；不支持拖拽排序（v2） |
| vxe-table 列宽 | FP 表格 | 写入 localStorage `cost_fp_cols` | 列隐藏不持久化 |
| stale 标识 | 结果页顶部 | 黄色横条 banner（不阻止下载） | 点击 "重新计算" 触发计算 |
| Reverse FP 表 | FP 编辑屏 | 反向模式下"采纳档位"前为只读，采纳后可编辑 | 采纳按钮在结果页 |
| Excel 下载 | 结果页底部 | 异步生成（Job + SSE 进度） | 完成后浏览器原生下载 |
| 反向水印 | Excel 与 UI | 全部 source=allocator 的 FP 显示 "预算倒推" 徽章 | Excel 封面页加注 "反向模式" |

### 6.7 关键 UI 决策

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

### 8.1 Plugin 元信息（符合 Claude Code 实际格式）

**`.claude-plugin/marketplace.json`**（用户添加 marketplace 的入口）：

```json
{
  "name": "cost-estimation-marketplace",
  "owner": {
    "name": "<author>",
    "email": "<author@example.com>"
  },
  "metadata": {
    "description": "软件造价评估工具集",
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

**`.claude-plugin/plugin.json`**（plugin 自身元信息）：

```json
{
  "name": "cost-estimation",
  "description": "软件造价评估 · NESMA 估算 · 双向（FP↔成本）",
  "version": "1.0.0",
  "author": { "name": "<author>", "url": "<repo-url>" },
  "commands": [
    "./commands/setup.md",
    "./commands/cost.md",
    "./commands/cost-stop.md"
  ],
  "license": "MIT",
  "keywords": ["cost-estimation", "function-points", "GB-T-36964", "CSBMK"]
}
```

### 8.2 用户安装与首次使用流程

由于 Claude Code 的 plugin 协议**没有 post_install 钩子**，依赖安装通过 slash 命令实现：

```
1. /plugin marketplace add github.com/your-org/cost-estimation
2. /plugin install cost-estimation
3. /cost-estimation:setup    ← 首次运行：建 venv、装依赖、初始化 SQLite
4. /cost                      ← 日常使用：启动后端 + 开浏览器
```

### 8.3 commands/setup.md（首次安装命令）

```markdown
---
description: 首次安装：建立 Python venv、安装依赖、初始化 SQLite + CSBMK 数据
allowed-tools: Bash, Read
---

执行以下步骤，按顺序：

1. 检测 Plugin 安装路径：
   ```bash
   PLUGIN_DIR="$HOME/.claude/plugins/data/cost-estimation"
   DATA_DIR="$HOME/.claude/projects/cost-estimation"
   ```

2. 创建数据目录：`mkdir -p "$DATA_DIR"/{db,uploads,exports}`

3. 在 `$PLUGIN_DIR/server` 下创建 venv 并安装依赖：
   ```bash
   cd "$PLUGIN_DIR/server"
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt --quiet
   ```

4. 初始化 SQLite + seed CSBMK®-202510 参数：
   ```bash
   python -m app.bootstrap \
     --db "$DATA_DIR/db/cost.sqlite" \
     --seed "$PLUGIN_DIR/server/app/data/csbmk_202510.json"
   ```

5. 报告："✓ 安装完成。运行 /cost 即可启动 Web 界面"
```

### 8.4 commands/cost.md（日常启动命令）

```markdown
---
description: 启动造价评估 Web 服务并打开浏览器
allowed-tools: Bash
---

启动后端：

1. 检查 8788 端口是否已占用，若占用则尝试 8789–8800 并写入 `~/.claude/projects/cost-estimation/.port`
2. 启动 uvicorn（后台）：
   ```bash
   nohup "$PLUGIN_DIR/server/.venv/bin/uvicorn" \
     app.main:app --host 127.0.0.1 --port "$PORT" \
     > /tmp/cost-estimation.log 2>&1 &
   ```
3. 轮询 `http://127.0.0.1:$PORT/health` 直到就绪（最多 10 秒）
4. `open http://127.0.0.1:$PORT/`
```

### 8.5 SKILL.md 触发与编排

```markdown
---
name: cost-estimation
description: Use when the user wants to do software cost estimation per Chinese GB/T 36964 standards, including forward calculation (scope → cost) or reverse derivation (target cost → function points). Triggers on phrases: "造价评估" / "功能点估算" / "软件成本" / "/cost".
---

## 使用流程

1. 用户调用 `/cost` 命令（由 commands/cost.md 处理）启动后端 + 打开浏览器
2. 用户在 FP 编辑页点 "AI 辅助提取" 时本 Skill 自动激活：
   - 通过 GET `/api/projects/{id}/uploads` 拿到上传文件清单
   - 读取项目目录下 `~/.claude/projects/cost-estimation/uploads/<id>/*.{pdf,docx,xlsx}`
   - 按 NESMA 估算法生成 FP 初稿（参考 reference/nesma-rules.md）
   - 调用 POST `/api/projects/{id}/functions/bulk` 写回（每条带 source=claude_draft）
3. 反向模式："AI 辅助分摊" 时本 Skill 同样激活，调 POST `/api/calc/allocate`

## 不要做的事

- 不在会话里逐个询问 FP 项（让用户在 Web 表格里编辑）
- 不修改 params_global 表（用 params_override）
- 不直接生成 Excel；调 GET `/api/reports/excel/{id}`
- 不主动启动后端（由 /cost 命令负责）
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

### 9.5 安全设计（CRITICAL — 防 localhost CSRF）

绑定 127.0.0.1 不等于安全。浏览器同时打开 `evil.com` 时，恶意 JS 可发请求到本机服务。**强制三层防护**：

### 9.5.1 启动随机 token

`/cost` 命令启动时生成一次性 token：

```python
# server/app/main.py
import secrets
TOKEN = secrets.token_urlsafe(32)
TOKEN_FILE = Path("~/.claude/projects/cost-estimation/.token").expanduser()
TOKEN_FILE.write_text(TOKEN)
```

打开浏览器时把 token 拼到 URL：`http://127.0.0.1:8788/?t=<token>`。前端从 URL 读后存入 sessionStorage。

### 9.5.2 中间件强制鉴权

```python
@app.middleware("http")
async def verify_token(request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    sent = request.headers.get("X-Auth-Token") or request.query_params.get("t")
    if sent != TOKEN:
        return JSONResponse(401, {"error": {"code": "UNAUTHORIZED", "message": "Invalid token"}})
    return await call_next(request)
```

### 9.5.3 Origin + CORS 白名单

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["X-Auth-Token", "Content-Type", "X-Requested-With"]
)

@app.middleware("http")
async def verify_origin(request, call_next):
    if request.method != "GET":
        origin = request.headers.get("Origin", "")
        if origin and not origin.startswith(f"http://127.0.0.1") and not origin.startswith(f"http://localhost"):
            return JSONResponse(403, {"error": {"code": "FORBIDDEN_ORIGIN"}})
    return await call_next(request)
```

### 9.5.4 文件上传白名单 + zip slip 防护

```python
ALLOWED_MIME = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}

import magic
def validate_upload(file: UploadFile) -> None:
    # 1. 扩展名白名单
    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".docx", ".xlsx", ".md"}:
        raise HTTPException(400, "INVALID_FILE_TYPE")
    # 2. MIME 内容嗅探
    head = file.file.read(2048); file.file.seek(0)
    if magic.from_buffer(head, mime=True) not in ALLOWED_MIME:
        raise HTTPException(400, "MIME_MISMATCH")
    # 3. 大小限制
    if file.size > 50 * 1024 * 1024:
        raise HTTPException(413, "FILE_TOO_LARGE")
```

### 9.5.5 危险操作二次确认

`DELETE /api/projects/{id}` 与 `POST /api/params/global/reset` 要求请求体含 `{ "confirm": "<project_name>" }` 或 `{ "confirm": "RESET_GLOBAL" }`。

---

## 10. 错误处理与边界条件

| 场景 | 处理 |
|---|---|
| 上传文件 > 50MB | 拒绝，返回 413 |
| Claude 提取的 FP 项数 = 0 | UI 提示"未识别到功能项，请检查文档质量或手动添加" |
| 反向计算预算 ≤ 0 | 返回 INVALID_PARAM "目标金额必须大于其他费用" |
| 城市/行业不在 CSBMK | 接受为自定义键，但提示"非内置参数，请在参数库手动维护" |
| 8788 端口被占用 | `/cost` 命令自动尝试 8789…8800；写入实际端口到 `.port` 文件 |
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
| Phase 6 · 打包安装 | Plugin 元信息 + commands/{setup,cost,cost-stop}.md | 2 天 |
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

- [ ] 二步安装：`/plugin install cost-estimation` → 用户运行 `/cost-estimation:setup` → setup 输出 "✓ 安装完成"
- [ ] `/cost` 唤起 → 后端启动 → 浏览器自动打开（携带 token）→ 可以走完 5 步向导导出 Excel
- [ ] 黄金测试（附录 D 算例）：输出 = 48.92 万元 ±0.01（中值），数据走 fixture `tests/golden/csbmk_202210.json`
- [ ] 反向模式：目标 50 万 → 三档 FP（乐观/中位/保守），forward(allocator(中位)) 误差 ≤1%
- [ ] 参数全量可改 + 重置 + 快照回滚
- [ ] 测试覆盖 ≥ 80%；mutation testing `core/*` 杀死率 ≥ 70%
- [ ] Excel 用 Office/WPS 正常打开，格式无错乱
- [ ] 安全：未带 token 访问任意 /api/* 路径返回 401
- [ ] 安全：跨域 fetch 到 8788 被 Origin 中间件拒绝

---

## 15. 后续扩展（v2+）

- COSMIC 方法（GB/T 42452）完整支持
- 多用户 + 角色权限 + 远程部署
- 历史 CSBMK 版本切换
- 评估报告 Word 导出
- 移动端响应式
- 与 Linear/Jira 集成（功能项导入导出）

---

<!-- AUTONOMOUS DECISION LOG -->
## 16. /autoplan 评审报告（2026-05-10）

### 16.1 跨阶段主题（多阶段独立涌现）

| 主题 | 出现阶段 | 信号强度 |
|---|---|---|
| **合规/审计可信链缺位** | CEO + Eng + DX | 高（3/4 阶段） |
| **反向模式存在合规红线 / 业务语义混乱** | CEO + Design + Eng | 高 |
| **缺失状态/错误路径未定义** | Design + Eng + DX | 高 |
| **安装路径不可靠（PEP 668 / 网络 / 命令一致性）** | Eng + DX | 高 |
| **Vue+FastAPI+SQLite 全栈可能过度工程** | CEO（双声音） | 中 |
| **API 风格不统一** | DX（双声音） | 中 |

### 16.2 决策审计追踪

| # | Phase | Decision | Classification | Principle | Rationale | 处置 |
|---|---|---|---|---|---|---|
| 1 | CEO | 是否做"对话主导 MVP"先验证用户 | **USER CHALLENGE** | — | 双模型都建议先做 5 天对话式 MVP 验证用户而非 28 天完整方案 | → 提交用户决策 |
| 2 | CEO | 是否补竞品矩阵与差异化定位 | TASTE | P1 完整 | 当前 0 字提到竞品 | → 推荐补 |
| 3 | CEO | 反向模式合规水印 | MECHANICAL | P1 完整 | 不加水印有合规红线 | → 必须加 |
| 4 | Design | 缺失状态矩阵（5 态 × 5 屏） | MECHANICAL | P1 完整 | 不补到实施阶段 4 程序员 4 版 | → 必须补 §6.5 |
| 5 | Design | 反向三档命名与推荐 | MECHANICAL | P5 显式 | "紧/标/松"对非技术用户不可判 | → 改"乐观/中位/保守" + P50 默认推荐 |
| 6 | Design | 可访问性基线（WCAG 2.1 AA） | TASTE | P1 完整 | 政府采购合规风险 | → 推荐补 §6.6 |
| 7 | Eng | PDR 三档业务语义重写 | MECHANICAL | P5 显式 | 当前注释"高生产率=小规模"业务含义错 | → 必须改算法文档 |
| 8 | Eng | localhost CSRF 防护（token + Origin + CORS） | MECHANICAL | P1 完整 | CRITICAL 安全 | → 必须加 |
| 9 | Eng | Allocator 锁定项分两段计算 | MECHANICAL | P5 显式 | locked 与 1% 容差冲突 | → 必须改 |
| 10 | Eng | fp_snapshots 触发器按 project_id 分组 | MECHANICAL | P5 显式 | cross-project 挤压 | → 必须改 |
| 11 | Eng | 文档解析异步化（threadpool/进程池） | MECHANICAL | P1 完整 | 50MB PDF 阻塞 event loop | → 必须改 |
| 12 | Eng | service 层 + EvaluationContext | TASTE | P5 显式 | 当前路由直接调 core 难测 | → 推荐补 |
| 13 | Eng | 黄金测试数据：fixture 内置 CSBMK®-202210 | MECHANICAL | P1 完整 | spec §1.2 与 §5.4 矛盾 | → 必须解决 |
| 14 | DX | `/cost-estimation:*` 命名空间统一 | MECHANICAL | P5 显式 | 三种风格混用 | → 必须改 |
| 15 | DX | 错误消息 problem+cause+fix+docs_url 四字段 | MECHANICAL | P1 完整 | 当前仅"返回 X" | → 必须改 |
| 16 | DX | setup preflight + 镜像 + 离线 wheels | MECHANICAL | P1 完整 | PEP 668 / 中国网络 | → 必须补 |
| 17 | DX | API 风格统一（resource over RPC 或反之） | TASTE | P5 显式 | 风格混搭 | → 推荐统一 |
| 18 | DX | Excel 批量导入 FP 一等公民化 | MECHANICAL | P5 显式 | 离线 / 跳过 AI 路径必备 | → 必须加 |
| 19 | DX | 验收标准 §14 与 §8.2 矛盾 | MECHANICAL | P5 显式 | 一处说"自动 venv"一处说"必须手跑 setup" | → 必须修 §14 |
| 20 | CEO | 6 个用户访谈 + 数据治理策略 | **USER CHALLENGE** | — | 双模型都建议在工程前先验证 | → 提交用户决策 |

### 16.3 双声音报告

- CEO Voices：Codex（10 项战略发现）+ Claude subagent（6 项），Consensus 6/6 confirmed
- Design Voices：Codex（9 项）+ Claude subagent（8 项），Consensus 7/7 confirmed
- Eng Voices：Codex（8 项）+ Claude subagent（10 项），Consensus 6/6 confirmed
- DX Voices：Codex（8 项）+ Claude subagent（8 项），Consensus 6/6 confirmed

### 16.4 用户拍板结果（D2 / D3）

- **D2 — UC-1：先做对话主导 MVP？** → 用户选 **B：仍按完整 Web 方案推进**，承担方向风险
- **D3 — UC-2：补访谈 + 竞品 + 合规链？** → 用户选 **C：两者都不做**，调研由产品负责人自行处理

### 16.5 v1.1 修订摘要

| # | 章节 | 修订内容 | 来源 |
|---|---|---|---|
| 1 | §5.2 | PDR 三档命名"乐观/中位/保守"+ 业务语义说明 + 推荐 P50 + 反向水印 | CRITICAL Eng+CEO |
| 2 | §5.3 | Allocator 两段计算（锁定项隔离）+ audit_tag=budget_derived | HIGH Eng |
| 3 | §6.4 | 新增"状态矩阵"——5 屏 × Loading/Empty/Error/Partial/Stale | CRITICAL Design |
| 4 | §6.5 | 新增"可访问性基线"——WCAG 2.1 AA、键盘、对比度、ARIA | HIGH Design |
| 5 | §6.6 | 新增"组件契约表"——8 个争议点视觉与交互定义 | CRITICAL Design |
| 6 | §9.5 | 新增"安全设计"——token + Origin + CORS + zip slip + 二次确认 | CRITICAL Eng |
| 7 | §4.3 | fp_snapshots 触发器按 project_id 分组；EvaluationContext 共享 | HIGH Eng |
| 8 | §14 | 验收标准修正：删除"自动 venv"承诺，统一为"二步安装" | CRITICAL DX |

### 16.6 待实施细节（v1.1 接受但未在 spec 内逐条展开）

下列改进点由 /autoplan 评审接受，将在编码阶段逐项落地（写入 commit 信息与代码注释）：

- **DX**：命令命名统一为 `/cost-estimation:setup` / `:start` / `:stop` / `:status`
- **DX**：错误响应统一 4 字段 `{ code, problem, cause, fix }` + `docs_url`
- **DX**：setup 加 preflight（python3 ≥ 3.10 + 磁盘 + 网络）+ 镜像 fallback `--index-url https://pypi.tuna.tsinghua.edu.cn/simple`
- **DX**：API 风格统一为资源型 `/api/projects/{id}/calculations/{forward,reverse,allocate}` + `/exports/excel`
- **DX**：Excel 批量导入作为一等公民——下载空白模板 + 上传写入
- **Eng**：openpyxl 5000+ 行流式 + 模板坏 fallback
- **Eng**：文档解析异步化（threadpool/进程池）+ SSE 进度
- **Eng**：测试加 mutation testing（mutmut，core/* ≥70% 杀死率）+ hypothesis property 测试
- **Eng**：黄金测试 fixture `tests/golden/csbmk_202210.json`（不进生产 seed）

### 16.7 USER CHALLENGES 拒绝结果备忘

用户明确拒绝以下两条改动：
- UC-1（先做 MVP）：**用户选直上完整方案**。承担"方向错误返工"风险。
- UC-2（补访谈/竞品/合规调研）：**用户选不做调研，按现方案推进**。所有差异化与合规可过审策略由产品负责人独立判断。

记录此项以便未来回溯：若产品上线后遇到"用户与预设不符"或"报告不被审计接受"，本节为 /autoplan 阶段已识别但被 deprioritized 的风险。


- COSMIC 方法（GB/T 42452）完整支持
- 多用户 + 角色权限 + 远程部署
- 历史 CSBMK 版本切换
- 评估报告 Word 导出
- 移动端响应式
- 与 Linear/Jira 集成（功能项导入导出）
