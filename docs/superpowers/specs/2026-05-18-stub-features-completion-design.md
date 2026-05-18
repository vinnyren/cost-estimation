# 三个待完善功能补全 — 设计文档

> 日期：2026-05-18 · 版本目标：v2.7 · 状态：已确认，待写实施计划

## 背景

v2.6 用户手册重写时发现三处「预留但未实装」的入口：

1. **全局审计页**（`/audit`）仍是占位卡片「全局审计聚合视图（跨项目）将在 v2.3 上线」。
2. **项目列表「批量导出 / 导入」** 两个按钮无任何点击逻辑。
3. **AI 任务面板「采纳 FP」按钮** 被 `disabled`，标注 `title="v3 实装"`。

本设计把这三个入口补全为真实功能。三者相互独立，合为一份 spec、一份实施
计划，分三个独立 section 实施。**无破坏性 schema 改动，无 alembic migration。**

## 现状（探查结论）

- `AuditGlobalView.vue` 仅 `<AuditView :global="true" />`；`AuditView.vue` 的
  `global` 分支渲染占位卡。后端只有 `GET /api/projects/{id}/audit`，无全局端点。
- `AuditLog` 模型字段：`id` / `project_id`(FK) / `ts` / `actor` / `action` /
  `target` / `diff_json`，有 `project` relationship。
- `ProjectList.vue` 工具栏有 `<button>导入</button>` 与 `<button>批量导出</button>`，
  均无 `@click`。
- `projects.copy` service 已实现「复制项目 + FP + 参数 override」的落库逻辑。
- FP `source` 取值含 `claude_draft`（"AI 草稿"，黄色高亮）与 `ai_extracted`
  （"AI 提取"，无高亮）。`AiTaskPanel.vue` 的「采纳 FP」按钮 `disabled`。

---

## 功能 1 — 全局审计聚合视图

把所有项目的审计事件合并成一条倒序时间线，每条标注所属项目。

### 后端

- 新增 `GET /api/audit`（全局，不带项目作用域）：
  - 查询参数 `limit`（默认 100，1–500）、`before_id`（keyset 分页游标）。
  - 跨所有项目列出 `AuditLog`，按 `ts` 倒序、同 `ts` 按 `id` 倒序。
  - join `Project` 取项目名。
- 新增 service `audit.list_global(db, limit, before_id)`，与现有
  `audit.list_for_project` 并列。
- 返回每条 = 现有审计字段（ts / actor / action / target / diff）
  **加** `project_id` + `project_name`。
- 响应信封沿用现有 audit 端点格式 `{success, data, error}`。

### 前端

- `api/audit.ts` 加 `listGlobal(limit?, beforeId?)`。
- `AuditView.vue` 的 `global` 分支：删除占位卡，改为调 `listGlobal`，
  渲染与项目审计同款的时间线组件；每条事件加一个项目名徽章标签。
  keyset「加载更多」逻辑复用现有实现。
- `AuditGlobalView.vue` 薄包装不变。

### 测试

- 后端：集成测试 —— 多项目混合事件按时间倒序、keyset 分页、空库。
- 前端：`AuditView` global 分支单测 —— 渲染时间线 + 项目标签、加载更多。

---

## 功能 2 — 项目批量导出 / 导入（JSON 备份 / 迁移）

勾选项目导出为 JSON，导入同格式 JSON 总是新建项目。

### 后端

- 新增 `POST /api/projects/export`，body `{ids: [...]}`：
  - 返回 JSON bundle：
    ```
    {
      "version": "2.7",
      "exported_at": "<ISO8601>",
      "projects": [
        {
          "<项目核心字段：name/project_type/phase/city/industry/client/
            evaluator/mode/target_cost/other_cost/include_ops/alpha_dev/
            fp_method/basis_data_ver>",
          "factors_dev": {...} | null,
          "factors_ops": {...} | null,
          "param_overrides": [ ... ],
          "function_points": [ {<FP 字段，不含 id/project_id>}, ... ]
        }
      ]
    }
    ```
  - **不含** id、created_at/updated_at、ai_tasks、audit_log、uploads、
    fp_snapshots / param_snapshots（运行时与历史数据）。
  - 不存在的 id 跳过；全部不存在返回空 `projects: []`。
- 新增 `POST /api/projects/import`，body 为上述 bundle：
  - 每个项目**生成新 id 新建**（不覆盖、不合并、不按名匹配）。
  - 落库逻辑参照 `projects.copy`：建项目 → 批量建 FP → 写参数 override。
  - 返回 `{imported: N, project_ids: [...]}`。
  - bundle 格式非法（缺 `projects` 数组、字段缺失）返回 400 + 可读原因。

### 前端

- `ProjectList.vue` 表格视图加复选框列 + 表头全选；`selectedIds` ref 跟踪选中。
- 「批量导出」：`selectedIds` 非空时可点（否则 disabled）→ 调 export →
  用 Blob 触发浏览器下载 `projects-export-YYYYMMDD.json`。
- 「导入」：隐藏 `<input type=file accept=".json">` → 选文件读文本 →
  调 import → 刷新列表 + 提示「已导入 N 个项目」。导入失败弹窗显示原因。
- 卡片视图不加复选框；该视图下「批量导出」点击时提示「请切换到表格视图勾选项目」。
- `api/projects.ts` 加 `exportProjects(ids)` 与 `importProjects(bundle)`。

### 测试

- 后端：export → import round-trip 集成测试（项目 + FP + override 完整还原、
  新 id、跳过不存在 id、非法 bundle 400）。
- 前端：`ProjectList` 选择态（全选/单选、按钮启用）、导入文件流程单测。

---

## 功能 3 — 采纳 FP（批量确认 AI 草稿）

AI 任务完成后，一键把该项目的 AI 草稿功能点标记为已采纳、脱离草稿高亮。

### 后端

- 新增 `POST /api/projects/{id}/functions/accept-drafts`：
  - 改动前先存一次 FP 快照（`fp_snapshots`，reason `accept_drafts`），便于回退。
  - 把该项目所有 `source='claude_draft'` 的功能点改为 `source='ai_extracted'`
    （保留 AI 来源标识，脱离「草稿」状态）。
  - 返回 `{accepted: N}`。
  - 项目不存在 → 404；无 claude_draft 行 → 返回 `{accepted: 0}`（非错误）。

### 前端

- `AiTaskPanel.vue` 的「采纳 FP」按钮去掉 `disabled` 与 `title="v3 实装"`；
  task 状态为 `done` 时可点。
- 点击 → 调 accept-drafts → 刷新 FP 列表 → 提示「已采纳 N 条功能点」。
- `FpEditor.vue` 中 `claude_draft` 行的黄色高亮因 `source` 变为 `ai_extracted`
  自然消失，无需改高亮逻辑。
- `api/functions.ts` 加 `acceptDrafts(projectId)`。

### 测试

- 后端：accept-drafts 集成测试（claude_draft → ai_extracted、快照已建、
  无草稿时 accepted=0、项目不存在 404）。
- 前端：`AiTaskPanel` 采纳按钮（done 时可点、调 API、刷新提示）单测。

---

## 不做的事（YAGNI）

- 全局审计不做项目筛选下拉、不做导出。
- 批量导出不做 zip 打包、不做 Excel 报告批量导出。
- 导入不做覆盖 / 合并 / 按名匹配 —— 一律新建。
- 采纳 FP 不做逐条对比勾选面板 —— 整批确认。

## 验收

- `/audit` 页显示跨项目合并审计时间线，每条带项目名。
- 项目列表勾选若干项目 → 批量导出 JSON → 导入该 JSON → 列表新增等量项目，
  FP 与参数 override 完整还原。
- AI 任务 `done` 后点「采纳 FP」→ FP 表草稿高亮消失，提示采纳条数。
- pytest / vitest / vue-tsc / build 全绿，无 alembic migration。
