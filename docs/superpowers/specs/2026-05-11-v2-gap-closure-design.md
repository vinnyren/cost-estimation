# 软件造价制作系统 · v2.0 Gap Closure 设计规范

**版本**：v2.0（v1.1 → v2.0 — feature gap closure）
**日期**：2026-05-11
**状态**：待评审
**依据**：v1.1 上线后审计发现 11 项功能缺失（详见 `2026-05-11-feature-gap-audit`）
**前置 Spec**：[2026-05-10-cost-estimation-design.md](./2026-05-10-cost-estimation-design.md)

---

## 1. 目标

v1.1 已交付：项目 CRUD、FP 编辑、参数 effective/override、正/反向 calc、Excel 报告、上传解析。但有 11 项 README 承诺的功能在 UI / AI 链路上未落地。本 v2.0 规范一次性补齐这些 gap。

**口号**：兑现 README 的所有 ✅ 项；补齐 ParamManager 的 4 个 v2 stub tab；接通 AI Plugin 链路。

## 2. 关键决策（已确认）

| # | 决策 | 选择 | 理由 |
|---|---|---|---|
| D1 | AI 集成路线 | Plugin 模式（宿主 Claude Code 通过 SKILL.md 调用） | 贴 Claude Code Plugin 设计本意；零 API Key 配置；与现有 commands/cost.md 架构对齐 |
| D2 | 发布节奏 | 单 PR / 单 v2.0 release / monolithic | 用户偏好，单作者无需多轮 review |

## 3. Gap → 实施模块映射

| GAP | 简述 | 后端变更 | 前端变更 | 风险 |
|---|---|---|---|---|
| A | AI 提取功能点 | SKILL.md prompt 优化 + commands/cost.md 链路 | FpEditor.vue 新增"等待 AI 提取"状态 | 低 |
| B | 17+ 调整因子 UI | calc.py 接收 dev_factor/ops_factor 真值 | ParamManager.vue 实装 factors_dev / factors_ops 两个 tab；Wizard 新增因子步骤 | 中 |
| C | AI 模块分摊 UI | 无（/calc/allocate 已就绪） | ResultView.vue 反向路径增加"生成模块分摊"面板 | 低 |
| D | 运维费率/生产率 UI | 无（数据已就绪） | ParamManager.vue 城市费率行增 ops 列；生产率 tab 增 productivity_ops 行 | 低 |
| E | alpha_dev / include_ops | 无 | Wizard 增 toggle / 滑块 + 说明 | 低 |
| F | 项目列表搜索/筛选/排序 | /api/projects 增 query params | ProjectList.vue 增搜索栏 + 多列排序 | 低 |
| G | client / evaluator 填写 | 无（schema 已就绪） | Wizard 第 1 步增可选字段 | 低 |
| H | ParamManager 快照 tab | /api/params/snapshots（新增） | ParamManager.vue 实装 snapshots tab | 中 |
| I | 项目复制 | POST /api/projects/{id}/copy（新增） | ProjectList.vue 行操作菜单"复制" | 中 |
| J | 项目审计日志 | audit_log 表 + 中间件 + GET /api/projects/{id}/audit | ProjectDetail 时间轴面板（或独立 view） | 中 |
| K | Phase 阶段 CF 预览 | 无 | Wizard 阶段步骤展示 CF 值 + 含义 | 低 |

---

## 4. 子系统设计

### 4.1 AI Plugin 链路（GAP-A, GAP-C）

**架构（保持 v1.1 已有 Plugin 形态）**：

```
用户 → 在 web 上传文档 → server 解析得 parsed_text → user 切到 Claude Code 终端运行 /cost
  → Claude Code 加载 commands/cost.md → 拉取 SKILL.md 的 prompt
  → 通过 server API GET /uploads/{id}/parsed 拉文本 → 生成 FP 草稿
  → 调 POST /functions/bulk?replace=false 写入（source="claude_draft"）
  → web 自动 refresh / 用户点刷新看到草稿
```

**变更点**：

1. **`commands/cost.md`** 增加显式工作流：先列出当前项目的 uploads，让 Claude 拉取每个 parsed_text，按 SKILL.md 模板生成 NESMA 5 类别 FP 列表，一次 bulk_write。
2. **`SKILL.md`** 已存在但需要审视：明确给出 NESMA 复杂度判定规则（low/average/high 怎么选）、UFP 表格、source 字段必须为 `"claude_draft"`。
3. **FpEditor.vue**：
   - 上传成功后 `window.alert(...)` 替换为 toast：「已上传。在 Claude Code 终端运行 `/cost` 让 Claude 提取 FP 草稿；或继续手动添加。」
   - 增加"刷新 FP"按钮 + 30s 自动 polling（仅当列表为空且有上传时）。
   - 新到的 `source="claude_draft"` 行用浅黄底色 + 「AI 草稿」徽标提示用户审核。
4. **AI 模块分摊（反向）**：ResultView.vue 反向路径在三档 FP 表下方增"生成模块分摊"按钮 → 显示 hint：「在 Claude Code 终端运行 `/cost allocate {projectId}`」+ polling FP 列表。新增 `commands/cost-allocate.md` 调用 /calc/allocate 端点。

**Trade-off**：用户必须在 Claude Code 上下文里才能用 AI。脱离 Claude Code 时手填 FP 是 fallback（已可用）。这是 D1 的逻辑后果，与 README "Claude Code Plugin"定位一致。

### 4.2 ParamManager v2（GAP-B 因子 + GAP-D 运维 + GAP-H 快照）

**当前状态**：6 tabs — rate / productivity 已实装；factors_dev / factors_ops / scale_change / snapshots 是 v2 stub。

**目标布局**（保留 6 tab 结构）：

| Tab | 内容 |
|---|---|
| 城市费率 | 37 城 × {dev, ops} 两列（**新增 ops 列**），可 inline 编辑 |
| 生产率 | productivity_dev × 7 行业（**新增 productivity_ops 行**），inline 编辑 |
| 开发因子 | 5 个因子（app_type / integrity_level / non_func / platform / team_bg）每个一个面板，展示 levels × multipliers 表，可编辑 multiplier |
| 运维因子 | 11 个因子同上 |
| 规模变更 | scale_change 子结构（增 / 减 / 修改 / 转换 / 变更率门槛），支持读写 |
| 参数快照 | 当前 effective params 快照列表 + "立即快照"按钮 + restore（v2 后端新增） |

**编辑模式**：使用 `PATCH /api/projects/{id}/params/override`（项目级）或 `PATCH /api/params/global`（全局）。tab 顶部显示当前作用域（"项目: T1" 或 "全局基准"）切换器。

**因子 UI 设计**（每个因子 1 张 collapsible 卡片）：

```
┌─ 应用类型（app_type） ─────────────┐
│ 影响：开发因子 dev_factor                │
│ ┌─────────┬────────────┬─────────┐  │
│ │ 级别    │ 名称       │ 系数    │  │
│ ├─────────┼────────────┼─────────┤  │
│ │ OLTP    │ 联机事务   │ 1.00    │  │
│ │ OLAP    │ 数据分析   │ 1.10    │  │
│ │ 嵌入式  │ 嵌入式系统 │ 1.15    │  │
│ │ Web     │ Web 应用   │ 1.05    │  │
│ └─────────┴────────────┴─────────┘  │
│ [复位为 CSBMK 默认]                  │
└──────────────────────────────────────┘
```

**Snapshots tab** 后端：新增

- `POST /api/params/snapshots` — 把当前 effective_params 序列化为 JSON 存 ParamSnapshot 表
- `GET /api/params/snapshots` — 列出快照（id, label, created_at, scope=global|project_id）
- `POST /api/params/snapshots/{id}/restore` — 用快照覆写 ParamGlobal / ParamOverride

**新表**：

```python
class ParamSnapshot(Base):
    __tablename__ = "param_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    scope = Column(String, nullable=False)  # "global" | project_id
    label = Column(String)  # 用户备注
    created_at = Column(DateTime, server_default=func.now())
    payload_json = Column(Text, nullable=False)
```

### 4.3 Wizard v2（GAP-E + GAP-G + GAP-K + 因子配置入口）

**当前**：5 步，无 client/evaluator，无因子，无 alpha 解释，无 include_ops 显式 toggle。

**新结构（7 步）**：

1. **基础信息**：name + city + industry + **client** + **evaluator**（后两个可选，留空时落库为 NULL，Excel 报告封面显示 `—`）
2. **项目类型**：dev_only / ops_only / dev_and_ops（radio）+ **include_ops** 自动联动（dev_and_ops 时强制 true）+ **alpha_dev** 滑块（仅 dev_and_ops 显示，范围 0.5–1.0，**默认 0.7**，含 tooltip："开发占总成本比例；运维占 1-α"）
3. **阶段（phase）**：5 阶段 radio + 当前 CF 值预览（GAP-K — 「您选择的阶段对应 CF 调整因子 = 1.05」）
4. **正向 / 反向**：mode + target_total（仅反向）
5. **开发因子**：5 个 dropdown（app_type / integrity_level / non_func / platform / team_bg）— 每个 dropdown 显示选项的 multiplier；底部显示「当前 dev_factor 链 = 1.21」实时计算
6. **运维因子**：11 个 dropdown（仅当 include_ops 时显示）— 同上
7. **确认**：全部参数预览 + "创建项目" 按钮

**关键变更**：calc.py 不再用默认 `dev_factor=1.0`，而是读取 Project.factors（新增字段）。

**Schema 变更**：

```python
# Project 表新增列（migration）
factors_dev_json = Column(Text)  # {"app_type": "OLTP", "integrity_level": "B", ...}
factors_ops_json = Column(Text)
```

**calc.py 集成**：

```python
factors_dev = json.loads(project.factors_dev_json or "{}")
dev_factor = dev_factor_chain(
    app_type=factors_dev.get("app_type"),
    non_func=factors_dev.get("non_func"),
    integrity=factors_dev.get("integrity_level"),
    platform=factors_dev.get("platform"),
    team_bg=factors_dev.get("team_bg"),
    factor_table=eff["factors_dev"],
)
```

如果 factors_dev_json 为空（v1.1 老项目），fallback 到 1.0 + 在 result.is_stale=True 加 warning_messages。

### 4.4 ProjectList v2（GAP-F）

**后端**：`GET /api/projects` 接受 query params（**全部可选；缺省 = 不筛 / 默认排序**，向后兼容 v1.1 调用方）

```
?q=<搜索词>           # name 子串匹配（不区分大小写）
&city=<城市>          # 精确匹配
&industry=<行业>
&phase=<阶段>
&mode=<forward|reverse>
&sort=<created_at|updated_at|name|target_total>   # 默认 created_at
&order=<asc|desc>                                   # 默认 desc
&page=<int>&size=<int>                              # 默认 page=1, size=50, max size=200
```

响应仍是现有 envelope `{success, data, error, meta}`，meta 增 `{total, page, size}` 供前端分页器用。

**前端**：ProjectList.vue 顶部增 toolbar：

```
┌──────────────────────────────────────────────────────────────┐
│ [🔍 搜索项目名…]  城市 ▼  行业 ▼  阶段 ▼  排序 ▼  [+ 新建] │
├──────────────────────────────────────────────────────────────┤
│ 名称           │ 城市     │ 行业       │ 阶段   │ 创建时间 │ │
│ ──────────────┼─────────┼───────────┼────────┼─────────┼ │
│ 智慧政务-2026  │ 北京     │ 电子政务   │ 招标   │ 05-10   │⋯│
└──────────────────────────────────────────────────────────────┘
```

行右侧 ⋯ 菜单：「打开 / 复制 / 删除」（GAP-I 复制接入此处）。

### 4.5 Project Lifecycle（GAP-I 复制 + GAP-J 审计）

**4.5.1 项目复制**

后端：`POST /api/projects/{id}/copy`

请求体 `{ "name": "新名称" }`，响应：新 project 完整对象。

实现：单事务复制 Project 行 + 所有 FunctionPoint 行（生成新 id，version=1）+ ParamOverride 行。**不复制** Result / FPSnapshot / Upload（让用户重新跑 calc / 上传）。

**4.5.2 审计日志**

新表：

```python
class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    ts = Column(DateTime, server_default=func.now(), index=True)
    actor = Column(String)  # "system" | "user" — v2 单用户始终 "user"，留字段为 v3 多用户预埋
    action = Column(String, nullable=False)  # "project.create" | "project.update" | "fp.bulk_write" | "params.override" | "calc.run" | "report.export" | ...
    target = Column(String)  # 受影响 entity ID（如 fp_id, snapshot_version）
    diff_json = Column(Text)  # 可选 before/after diff
```

**写入位置**：FastAPI middleware 拦截所有 PATCH/POST/DELETE on `/api/projects/*`，写入 audit_log。

**读取**：`GET /api/projects/{id}/audit?limit=100&before_id=N`（cursor 分页）。

**前端**：ProjectList 行 ⋯ 菜单 → "审计日志" → modal 时间轴。

---

## 5. 数据迁移

### 5.1 新表 / 新列

通过 alembic migration 添加：

1. `param_snapshots` 表（4.2）
2. `audit_log` 表（4.5.2）
3. `projects.factors_dev_json` + `projects.factors_ops_json` 列（4.3）

### 5.2 v1.1 老项目兼容

- `factors_*_json` IS NULL → calc 用 1.0 + Result.is_stale + 在 warning_messages 加："此项目缺少调整因子配置，已按 1.0 计算。请在项目设置中补充。"
- 所有原 Wizard 流程仍可用（新字段都是可选）
- 已存在的 ProjectOverride / ParamGlobal 不变
- 现有 8a2e6b41c3d7 alembic head 不动；新 revision 基于它

### 5.3 已废弃 / 改名

无。所有变更都是增量。

---

## 6. 测试计划

### 6.1 单元 / 集成（pytest）

| 模块 | 关键测试 |
|---|---|
| AI Plugin | `commands/cost.md` smoke：mock 一个 parsed_text → 验证 SKILL.md prompt 不漏 NESMA 5 类别 |
| ParamManager 因子 tab | E2E：开 dropdown → 改 multiplier → 重算 result → 数值变化符合预期 |
| Snapshots | 创建快照 → 改全局 → restore → 值还原 |
| Wizard 因子步骤 | 完成 wizard → 第一次 calc 用真因子，dev_factor ≠ 1.0 |
| ProjectList query | q + city + industry 组合，分页 |
| 项目复制 | 复制后 FP 行数 / 参数 override 一致；新 project_id ≠ 旧 |
| Audit log | PATCH 项目 → audit_log 多一行；DELETE 项目 → 所有相关 audit 行 cascade 删 |

### 6.2 前端（vitest）

- ParamManager 6 tab 都能渲染
- Wizard 7 步流程不抛错；factor dropdown 有正确选项
- ProjectList toolbar 触发 query params

### 6.3 E2E（Playwright）

- 完整正向流程（含 wizard 因子）→ Result 数字与手动计算一致
- 完整反向流程 → 三档 FP → 模拟 AI 分摊
- 项目复制流程
- 审计日志渲染

### 6.4 覆盖率目标

后端 ≥ 80%（已 90+%），前端 ≥ 70%（当前 ~65%）。

---

## 7. 实施顺序（单 PR 内）

虽然单 PR，commit 序列建议：

1. `feat(server): factors_dev_json + factors_ops_json on Project + alembic migration`
2. `feat(server): param_snapshots 表 + 4 个 endpoint`
3. `feat(server): audit_log middleware + endpoint + 表`
4. `feat(server): /projects/{id}/copy + tests`
5. `feat(server): /projects query params (q/city/industry/sort/page)`
6. `feat(server): calc.py 读取 project.factors_*_json`
7. `feat(web): ParamManager v2 — factors_dev/ops + scale_change + snapshots tab + ops 列`
8. `feat(web): Wizard v2 — 7 步 + factor dropdowns + alpha + client/evaluator`
9. `feat(web): ProjectList v2 — toolbar + 行菜单 + 复制 + 审计`
10. `feat(web): FpEditor — AI Plugin hint + claude_draft 高亮 + 自动 polling`
11. `feat(web): ResultView — 反向 allocator UI`
12. `chore: SKILL.md polish + commands/cost.md 新工作流 + commands/cost-allocate.md`
13. `docs: README v2.0 章节 + user-guide v2.0 章节`
14. `chore: bump 1.1.0 → 2.0.0`

每个 commit 单独可跑 pytest + vitest 不破坏。

---

## 8. 范围外（保留 v3）

- 多用户协作 / 用户系统
- 远程部署
- 移动端适配
- COSMIC 完整支持
- 历史 CSBMK 版本切换
- WebSocket 实时更新
- 项目导出/导入 JSON（GAP-I 的扩展，本 v2 只做 in-DB 复制）
- 批量操作（批量删除 / 归档）

---

## 9. 落地时的小决策（已默认 / 可微调）

| # | 议题 | 默认 | 备注 |
|---|---|---|---|
| 1 | AI Plugin 等待 polling 间隔 | 30s + 用户可点"立即刷新" | 减少无意义请求 |
| 2 | Audit log 中间件 method 过滤 | 仅 PATCH/POST/PUT/DELETE | GET 不写日志，防 noise |
| 3 | 项目复制是否带 client/evaluator | 是 | 用户可在新项目里改 |
| 4 | ParamManager 作用域切换 UI | tabs 顶部下拉「全局基准 / 当前项目」 | 单一路由，避免路径分裂 |
| 5 | factor dropdown 默认值 | 取 CSBMK level 中第一个（如 app_type 默认 OLTP）| Wizard 不强制改 |
| 6 | Wizard 第 7 步"创建"按钮 disabled 条件 | name 非空 + 必填字段已选 | 因子可不填（fallback 1.0）|

实施 PR 中遇到分歧再回到这张表。
