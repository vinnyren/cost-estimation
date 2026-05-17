---
description: 启动造价评估 Web 服务（无参）或对 <project_id> 执行 AI 功能点提取
allowed-tools: Bash, Read
---

# /cost — 造价评估启动 / AI 功能点提取

参数：

- **无参数**：启动 Web 后端 + 浏览器（首次使用走这条）
- **`<project_id>`**：对该项目执行 AI FP 提取（要求后端已在运行 / 已上传文档）

---

## 分支 A — 无参数：启动 Web 服务

> 用户没传 project_id 时走这条分支。下方步骤 1-6 是启动流程；执行完毕后给出 URL 并退出，不进入分支 B。

1. 定义路径：
   ```bash
   PLUGIN_DIR="$HOME/.claude/plugins/cache/cost-estimation"
   [ -d "$PLUGIN_DIR" ] || PLUGIN_DIR="$HOME/.claude/plugins/data/cost-estimation"
   DATA_DIR="$HOME/.claude/projects/cost-estimation"
   mkdir -p "$DATA_DIR"
   ```

2. 检测 8788 端口是否占用，若占用则尝试 8789–8800：
   ```bash
   PORT=""
   for p in 8788 8789 8790 8791 8792 8793 8794 8795 8796 8797 8798 8799 8800; do
     if ! lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1; then
       PORT=$p
       break
     fi
   done
   [ -z "$PORT" ] && { echo "✗ 8788–8800 端口全部占用"; exit 1; }
   echo "$PORT" > "$DATA_DIR/.port"
   ```

3. 生成一次性 token：
   ```bash
   TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
   echo "$TOKEN" > "$DATA_DIR/.token"
   chmod 600 "$DATA_DIR/.token"
   ```

4. 启动 uvicorn（后台），把 PID 写入 .pid：
   ```bash
   if [ ! -x "$PLUGIN_DIR/server/.venv/bin/uvicorn" ]; then
     echo "✗ 未找到 venv：请先运行 /cost-estimation:setup"
     exit 1
   fi
   cd "$PLUGIN_DIR/server"
   COST_AUTH_TOKEN="$TOKEN" \
   COST_DATA_DIR="$DATA_DIR" \
   COST_WEB_DIST_DIR="$PLUGIN_DIR/web/dist" \
   nohup ".venv/bin/uvicorn" \
     app.main:app --host 127.0.0.1 --port "$PORT" \
     > /tmp/cost-estimation.log 2>&1 &
   echo $! > "$DATA_DIR/.pid"
   ```

5. 轮询 `http://127.0.0.1:$PORT/health` 直到就绪（最多 10 秒）：
   ```bash
   READY=false
   for i in $(seq 1 20); do
     if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
       READY=true
       break
     fi
     sleep 0.5
   done
   if [ "$READY" != "true" ]; then
     echo "✗ 后端启动超时（10s）。日志: /tmp/cost-estimation.log"
     exit 1
   fi
   ```

6. 在默认浏览器打开（携带 token）：
   ```bash
   URL="http://127.0.0.1:$PORT/?t=$TOKEN"
   case "$(uname -s)" in
     Darwin) open "$URL" ;;
     Linux)  xdg-open "$URL" ;;
     MINGW*|MSYS*|CYGWIN*) start "$URL" ;;
     *) echo "请手动打开：$URL" ;;
   esac
   echo "✓ 已启动: $URL"
   echo "  日志: /tmp/cost-estimation.log"
   echo "  停止: 运行 /cost-estimation:cost-stop"
   ```

启动完成后回复用户：

> "Web 已启动：<URL>。在浏览器创建项目后，回到终端运行 `/cost <project_id>` 让 AI 帮你抽取 FP。"

---

## 分支 B — 有参数 `<project_id>`：AI 功能点提取

> 用户传入 project_id 时走这条分支，按 SKILL.md "AI 功能点提取" 章节执行。

### Step 1：读取鉴权信息 + 健康检查

```bash
DATA_DIR="$HOME/.claude/projects/cost-estimation"
PORT=$(cat "$DATA_DIR/.port" 2>/dev/null)
TOKEN=$(cat "$DATA_DIR/.token" 2>/dev/null)
if [ -z "$PORT" ] || [ -z "$TOKEN" ]; then
  echo "✗ 找不到运行中的服务。请先运行 /cost-estimation:cost 启动。"
  exit 1
fi
BASE="http://127.0.0.1:$PORT"
curl -fsS "$BASE/health" >/dev/null || {
  echo "✗ 后端无响应。请先运行 /cost-estimation:cost 启动。"
  exit 1
}
```

> 鉴权 fallback：如果 `~/.cost-estimation/auth-token.txt` 或环境变量 `COST_AUTH_TOKEN` 存在，可直接读那个 token；如果两处都没有，让用户在 `web/.env` 中看 `VITE_COST_AUTH_TOKEN` 字段。但在 Plugin 安装模式下，token 始终落在 `$DATA_DIR/.token`。

所有后续 `/api/*` 请求带 header：

```
X-Auth-Token: $TOKEN
Content-Type: application/json
```

**T0 — 创建 AI 任务（让前端 polling 看到进度）**

```bash
PROJECT_ID="<project_id>"   # 替换为用户传入的实际 project_id
TASK_ID=$(curl -fsS -X POST "$BASE/api/ai-tasks" \
  -H "X-Auth-Token: $TOKEN" \
  -H "content-type: application/json" \
  -d "{\"project_id\":\"$PROJECT_ID\",\"kind\":\"extract\"}" | jq -r .id)
echo "AiTask created: $TASK_ID"
```

`$TASK_ID` 在后续 5 次 PATCH 中使用。PATCH 失败不阻断主流程（用 `|| true` 兜底）。

### Step 2：拉取项目的 upload 列表

```http
GET /api/projects/{project_id}/uploads
```

- 如果返回空：告诉用户 "请先在浏览器上传需求 / 设计文档：$BASE/projects/{project_id}/functions"，然后退出
- 否则对每个 upload 调：

```http
GET /api/projects/{project_id}/uploads/{upload_id}/parsed
```

拿到 `parsed_text`（纯文本，已由后端预解析）。把所有 upload 的文本拼起来作为后续分析的素材。

**T1 — 文档已解析**

```bash
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"status":"running","progress_pct":10,"stage_log_append":"✓ 文档解析"}' \
  > /dev/null || true
```

### Step 3：按 NESMA 5 类别生成 FP 列表

按 SKILL.md "AI 功能点提取 — Step 2/3" 的 prompt 把文本里描述的功能逐条归类。

#### 3.0 必须提取三级模块层级（强制）

每一条 FP **必须**带上完整的模块层级 —— `subsystem`（子系统）、
`l1_module`（一级模块）、`l2_module`（二级模块）。这不是可选项。

**源文档是结构化表格（功能清单 Excel）时**：直接按列读取层级。
常见列名映射（大小写 / 同义词都要识别）：

| 文档列名 | FP 字段 |
|---|---|
| 子系统 / 软件开发 / 系统 | `subsystem` |
| 一级模块 / 一级目录 / 一级功能 | `l1_module` |
| 二级模块 / 二级目录 / 功能模块 | `l2_module` |
| 子功能 / 功能点计数项名称 / 功能名称 | `name` |
| 功能项描述 / 功能说明 / 描述 | `description` |

表格里层级单元格常用**纵向合并**（一个子系统跨多行）。解析纯文本时
若某行层级列为空，**沿用上一非空行的值**（向下填充），不要留空。

**源文档是使用手册 / 需求文档（无表格）时**：从章节标题层级推断 ——
一级标题 → `subsystem`，二级标题 → `l1_module`，三级标题 → `l2_module`，
正文里的每个功能动作 → 一条 FP。手册没有明确三级时，至少要给出
`subsystem` + `l1_module`；`l2_module` 可为空但前两级不许空。

**校验**：写入前自查 —— 若有 FP 的 `subsystem` 或 `l1_module` 为空，
说明层级没提取干净，回到文档重新归类，不要直接写入空层级的 FP。

**T2 — 章节切分完成**

```bash
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"progress_pct":30,"stage_log_append":"✓ 章节切分 + 三级模块层级"}' \
  > /dev/null || true
```

- **EI**（External Input）：增/改/删事件，例 "提交订单"
- **EO**（External Output）：派生 / 计算输出，例 "生成报表"
- **EQ**（External Query）：纯查询 / 列表
- **ILF**（Internal Logical File）：本系统维护的逻辑文件，例 "用户表"
- **EIF**（External Interface File）：外部维护、本系统读取的接口文件

复杂度按下表（DET = 字段数，FTR = 引用文件数，RET = 记录元素类型数）：

| 类别 | low | average | high |
|---|---|---|---|
| EI | 3 | 4 | 6 |
| EO | 4 | 5 | 7 |
| EQ | 3 | 4 | 6 |
| ILF | 7 | 10 | 15 |
| EIF | 5 | 7 | 10 |

判定：
- EI/EO/EQ：low if DET<5 ∨ FTR<2；high if DET≥10 ∧ FTR≥3；else average
- ILF/EIF：low if DET<20 ∧ RET<2；high if DET≥50 ∨ RET≥6；else average
- 信息不足时**默认 average**

**T3 — 类别归类完成**

```bash
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"progress_pct":55,"stage_log_append":"✓ EI/EO/EQ/ILF/EIF 类别归类"}' \
  > /dev/null || true
```

### Step 4：批量写入

```http
POST /api/projects/{project_id}/functions/bulk
Content-Type: application/json
X-Auth-Token: $TOKEN

{
  "items": [
    {
      "subsystem": "电子结算",
      "l1_module": "交易机构资金管理",
      "l2_module": "资金查询",
      "name": "客户账户查询",
      "category": "EQ",
      "complexity": "average",
      "ufp": 4,
      "us": 4,
      "source": "claude_draft",
      "description": "可查询商户交易账户、保证金账户、欠款账户、白条账户资金明细"
    }
  ],
  "replace": false
}
```

**关键约束**：

- `subsystem` + `l1_module` **必填**（见 3.0），`l2_module` 尽量填、实在无层级才留空
- `source` 必须是 `"claude_draft"`（前端会高亮提示用户审核）
- `ufp` 与 `us` 必须等于上表对应单元格的 NESMA 默认值（不要自创）
- `replace=false` 走追加模式，不覆盖用户已手填的 FP
- 一次性提交完整 FP 清单（覆盖文档里全部业务流程），避免多次半成品调用

**T4 — FP 表写入完成**

```bash
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"progress_pct":85,"stage_log_append":"✓ 写入 FP 表"}' \
  > /dev/null || true
```

### Step 5：完成后回复用户

> "已根据文档生成 N 条 FP 草稿，写入项目 {id}。请在浏览器审核 / 调整：$BASE/projects/{id}/functions"

**T5 — 任务完成**

```bash
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d "{\"status\":\"done\",\"progress_pct\":100,\"stage_log_append\":\"✓ 完成\",\"output_json\":\"{\\\"task_id\\\":\\\"$TASK_ID\\\"}\"}" \
  > /dev/null || true
echo "✅ AiTask $TASK_ID marked done"
```

---

## 错误兜底：标记任务 failed

如果上述任何步骤失败，在退出前调用：

```bash
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"status":"failed","error_message":"提取流程中断"}' \
  > /dev/null || true
```

---

## 不要做的事

- 不要在终端逐条问 FP（用户在 Web 表格里编辑更高效）
- 不要修改 `params_global`（改 project override 用 `PATCH /api/projects/{id}/params/override`）
- 不要绕过 token 鉴权
- 不要在分支 B 里自动启动后端（让用户先跑无参 `/cost`）
