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
