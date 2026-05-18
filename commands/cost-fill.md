---
description: 对 <project_id> 按反算模块树缺口 AI 补全功能点草稿
allowed-tools: Bash, Read
---

# /cost-fill — 反算补全功能点

参数：**`<project_id>`**（必填）。对该项目执行反算缺口补全。

要求：后端已在运行、项目为反算模式且已设置目标造价。

## Step 1：读取鉴权信息 + 健康检查

```bash
DATA_DIR="$HOME/.claude/projects/cost-estimation"
PORT=$(cat "$DATA_DIR/.port" 2>/dev/null)
TOKEN=$(cat "$DATA_DIR/.token" 2>/dev/null)
if [ -z "$PORT" ] || [ -z "$TOKEN" ]; then
  echo "✗ 找不到运行中的服务。请先运行 /cost-estimation:cost 启动。"
  exit 1
fi
BASE="http://127.0.0.1:$PORT"
curl -fsS "$BASE/health" >/dev/null || { echo "✗ 后端无响应。请先运行 /cost-estimation:cost 启动。"; exit 1; }
```

所有 `/api/*` 请求带 header `X-Auth-Token: $TOKEN` 与 `Content-Type: application/json`。

## Step 2：创建 reverse_fill 任务

```bash
PROJECT_ID="<project_id>"
TASK_ID=$(curl -fsS -X POST "$BASE/api/ai-tasks" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d "{\"project_id\":\"$PROJECT_ID\",\"kind\":\"reverse_fill\"}" | jq -r .id)
echo "AiTask created: $TASK_ID"
```

`$TASK_ID` 在后续 PATCH 进度上报中使用。PATCH 失败不阻断主流程（用 `|| true` 兜底）。

## Step 3：拉取反算结果（含三级模块树）

```bash
curl -fsS -X POST "$BASE/api/calc/reverse" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d "{\"project_id\":\"$PROJECT_ID\"}" > /tmp/reverse-$TASK_ID.json
```

读 `/tmp/reverse-$TASK_ID.json` 的 `module_allocation_tree`。进度上报：

```bash
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"status":"running","progress_pct":15,"stage_log_append":"✓ 加载反算模块树"}' \
  > /dev/null || true
```

## Step 4：逐叶子计算缺口并生成 FP 草稿

遍历 `module_allocation_tree` 的每个二级叶子节点：

- **缺口（`delta_ufp` > 0）**：为该叶子模块生成若干功能点草稿，UFP 合计 ≈ `delta_ufp`。
  每条草稿要给出 `name`（结合 `subsystem/l1_module/l2_module` 语境的合理功能名）、
  `description`（一句话功能说明）、`category`（EI/EO/EQ/ILF/EIF）、`det` + `ret`/`ftr`
  （按 IFPUG 估计）。`source` 必须为 `"reverse_draft"`。
- **超出（`delta_ufp` < 0）**：不新增 FP，按比例下调该叶子模块现有 FP 的 `us`。
  这是反算补全的预期行为（用户主动触发「按反算补全 FP」），只下调规模、不删条目。
  做法：对该叶子模块 `GET /api/projects/<project_id>/functions`，按
  `subsystem` + `l1_module` + `l2_module` 过滤出属于它的 FP，算
  `ratio = allocated_ufp / current_ufp`（0 < ratio < 1），逐条
  `PATCH /api/projects/<project_id>/functions/<fp_id>` 把 `us` 改为
  `round(us × ratio, 2)`。`ufp` 不动（IFPUG 计数值），只调 `us`（规模口径）。
  下调完成后 stage_log 注明「模块 X 现有 FP 规模已按 ratio 下调」。

  下调单条 FP 的命令形如：
  ```bash
  curl -fsS -X PATCH "$BASE/api/projects/$PROJECT_ID/functions/<fp_id>" \
    -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
    -d "{\"us\": <us×ratio>}" > /dev/null || true
  ```

若项目已上传文档，先 `GET /api/projects/$PROJECT_ID/uploads` 拿语境，让草稿名称
更贴合真实需求。进度上报 45：

```bash
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"progress_pct":45,"stage_log_append":"✓ 计算各叶子缺口"}' > /dev/null || true
```

## Step 5：批量写入 FP 表

```bash
curl -fsS -X POST "$BASE/api/projects/$PROJECT_ID/functions/bulk" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"items":[ ... reverse_draft 草稿数组 ... ],"replace":false}'
```

- `source` 必须为 `"reverse_draft"`，`replace=false`（追加，不覆盖用户 FP）。
- `subsystem` + `l1_module` 必填，`l2_module` 用叶子节点的 `l2_module`。
- `ufp` / `us` 按 IFPUG 类别 × 复杂度取值；草稿合计 ≈ 各叶子缺口。

进度上报 80，完成后置 done：

```bash
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"progress_pct":80,"stage_log_append":"✓ 生成补全 FP 草稿"}' > /dev/null || true
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"status":"done","progress_pct":100,"stage_log_append":"✓ 完成"}' > /dev/null || true
echo "✅ AiTask $TASK_ID marked done"
```

## 错误兜底

任何步骤失败，退出前调用：

```bash
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"status":"failed","error_message":"反算补全流程中断"}' > /dev/null || true
```

## 不要做的事

- 不要**删除**用户已有 FP（超出场景只按比例下调现有 FP 的 `us`，不删条目、不动 `ufp`）。
- 缺口场景写入的草稿一律 `source="reverse_draft"`、`replace=false`，不覆盖用户 FP。
- 不要修改 params_global。
- 不要绕过 token 鉴权。
- 不要在本命令里自动启动后端（让用户先跑无参 `/cost-estimation:cost`）。
