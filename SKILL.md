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
2. 用户在 FP 编辑页点 "AI 辅助提取" 或在终端直接运行 `/cost <project_id>` — 见下方 NESMA 提取 prompt
3. 反向模式："AI 辅助分摊" 见 `commands/cost-allocate.md`

## 调用 API 时的鉴权

读取 token：

```bash
TOKEN=$(cat ~/.claude/projects/cost-estimation/.token)
PORT=$(cat ~/.claude/projects/cost-estimation/.port)
curl -H "X-Auth-Token: $TOKEN" "http://127.0.0.1:$PORT/api/projects"
```

所有 `/api/*` 请求必须携带 `X-Auth-Token: <token>` header（或 `?t=<token>` query）。

---

## AI 功能点提取 — Plugin 工作流（v2.0）

当用户在 Claude Code 终端运行 `/cost <project_id>`，按以下 prompt 操作：

### Step 1：拉取上传文档的 parsed_text

调 `GET /api/projects/{project_id}/uploads` — 拿到 upload list。
对每个 upload 调 `GET /api/projects/{project_id}/uploads/{upload_id}/parsed`
得到纯文本。

### Step 2：根据文本生成 NESMA FP 列表

把文档里描述的"功能"按 NESMA 5 类别归类：

- **EI（External Input）**：用户向系统提交的事件 — 增/改/删。例：注册用户、提交订单
- **EO（External Output）**：系统对外输出经过派生 / 计算的数据。例：生成报表、对账单
- **EQ（External Query）**：纯粹查询 / 检索。例：列表查询、按 ID 查
- **ILF（Internal Logical File）**：系统内维护的逻辑文件 / 数据集。例：用户表、订单表
- **EIF（External Interface File）**：外部系统维护、本系统读取的接口文件。例：调用第三方支付的回调

### Step 3：为每个 FP 选复杂度

按 NESMA 估算法标准 UFP 表：

| 类别 | low | average | high |
|---|---|---|---|
| EI | 3 | 4 | 6 |
| EO | 4 | 5 | 7 |
| EQ | 3 | 4 | 6 |
| ILF | 7 | 10 | 15 |
| EIF | 5 | 7 | 10 |

复杂度判定（DET = 字段数，FTR = 引用文件数，RET = 记录元素类型数）：
- EI/EO/EQ: low if DET<5 ∨ FTR<2; high if DET≥10 ∧ FTR≥3; else average
- ILF/EIF: low if DET<20 ∧ RET<2; high if DET≥50 ∨ RET≥6; else average

如果文档信息不足，**默认 average**。

### Step 4：调用 bulk_write 写入

```http
POST /api/projects/{project_id}/functions/bulk
Content-Type: application/json
X-Auth-Token: <token>

{
  "items": [
    {
      "name": "用户注册",
      "category": "EI",
      "complexity": "low",
      "ufp": 3,
      "us": 3,
      "source": "claude_draft",
      "description": "用户填写邮箱+密码，提交"
    },
    ...
  ],
  "replace": false
}
```

**关键约束**：
- `source` 必须是 `"claude_draft"`，让前端高亮提示用户审核
- `ufp` 与 `us` 应等于上表对应单元格的 NESMA 默认值（不要自创）
- 优先生成完整 FP 列表（覆盖全部业务流程），而非半成品
- replace=false：追加模式，不覆盖用户已手填的 FP

### Step 5：完成后回复用户

> "已根据文档生成 N 条 FP 草稿，已写入项目 {id}。请在浏览器 FP 编辑屏审核 / 调整。"

---

## AI 模块分摊 — `/cost-allocate <project_id>`（v2.0）

仅对反向（reverse）模式项目可用。详见 `commands/cost-allocate.md`。

---

## 不要做的事

- 不在会话里逐个询问 FP 项（让用户在 Web 表格里编辑）
- 不修改 `params_global` 表（始终用 `PATCH /api/projects/{id}/params/override`）
- 不直接生成 Excel；调用 `GET /api/reports/excel/{project_id}`
- 不主动启动后端（由 `/cost` 命令负责）
- 不绕过 token 鉴权（所有 `/api/*` 请求必须携带 `X-Auth-Token` 或 `?t=` 查询）

## 参考文件

- `reference/nesma-rules.md` — NESMA 估算 5 大类详细规则
- `reference/csbmk-overview.md` — CSBMK®-202510 数据集结构与字段说明
