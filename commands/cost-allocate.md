---
description: AI 模块分摊（仅反向模式）— 把目标 US 拆成多个模块草稿写回 FP 表
allowed-tools: Bash, Read
---

# /cost-allocate — AI 模块分摊（反向模式）

参数：**`<project_id>`（必填）**

> 仅对反向（reverse）模式项目可用。把反向求解出的中位档 US 总量按 AI 推断的模块清单拆分，写回 FP 表作为草稿，由用户在 Web 审核。

---

## Step 1：读取鉴权 + 健康检查

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

所有 API 请求带 `X-Auth-Token: $TOKEN`。

---

## Step 2：确认项目处于反向模式

```http
GET /api/projects/{project_id}
```

- 如果 `mode != "reverse"`：告诉用户 "请先在浏览器把项目切到反向模式，并填写 `target_total`：$BASE/projects/{id}/wizard"，然后退出
- 否则读取项目字段：`name`、`description`、`industry`、`city`、`phase`、`target_total`，留作 Step 4 推断模块清单时的上下文

---

## Step 3：拿 P50 档的 scale_us

让 server 现算一次反向（也可直接读用户最近一次在浏览器跑过的结果，但跑一次更稳）：

```http
POST /api/calc/reverse
Content-Type: application/json
X-Auth-Token: $TOKEN

{
  "project_id": "<id>",
  "target_total": <项目 target_total>
}
```

返回 `reverseResult`。从 `scale_adjusted_bands.P50.scale_us` 字段拿到中位档总 US（单位：标准人月）。同时记下 `cf_used` 字段，留作 Step 5 调 allocator 时传 `cf`。

> 如果 server 没返回 `cf_used`，fallback 调 `GET /api/params/effective?project_id={id}` 拿 `cf[<project.phase>]`。

---

## Step 4：让 AI 推断模块清单

根据 Step 2 拿到的项目元数据（name / description / industry / city）推断该项目应包含哪些模块。示例启发：

| 项目类型示例 | 典型模块 |
|---|---|
| 智慧政务 / 电子政务 | 前端门户、后台管理、数据接入、权限中心、用户中心、报表中心 |
| 电商交易 | 商品中心、订单中心、支付网关、营销中心、用户中心、客服后台 |
| 物联网 / 智慧园区 | 设备接入、数据采集、规则引擎、监控大屏、运维后台 |
| 教育 / 学习平台 | 课程中心、学员中心、教学后台、直播 / 录播、考试系统 |

为每个模块估一个相对权重（complexity-aware）：

- 纯展示前端：**1.0**
- 复杂业务后台 / 工作流：**1.5–2.0**
- 简单接入 / 配置类：**0.5–0.8**
- 数据 / 报表 / BI：**1.2–1.5**
- 鉴权 / 用户中心（标准化）：**0.8–1.0**

数量建议 5–10 个模块。如果项目描述非常薄，给出 5 个通用模块（前端、后端管理、数据层、用户中心、报表）即可。

---

## Step 5：调用 allocator

```http
POST /api/calc/allocate
Content-Type: application/json
X-Auth-Token: $TOKEN

{
  "project_id": "<id>",
  "target_us": <P50 scale_us>,
  "drafts": [
    {"name": "前端门户", "weight": 1.0, "locked": false},
    {"name": "后台管理", "weight": 2.0, "locked": false},
    {"name": "数据接入", "weight": 0.8, "locked": false},
    {"name": "权限中心", "weight": 1.0, "locked": false},
    {"name": "用户中心", "weight": 1.0, "locked": false},
    {"name": "报表中心", "weight": 1.5, "locked": false}
  ],
  "cf": <reverseResult.cf_used>
}
```

返回结构示意：

```json
{
  "items": [
    {"name": "前端门户", "assigned_us": 4.5, ...},
    {"name": "后台管理", "assigned_us": 9.0, ...},
    ...
  ]
}
```

每个 `assigned_us` 是按权重比例分配出来的中位档 US。

---

## Step 6：把每个模块写回 FP 表（bulk_write）

```http
POST /api/projects/{project_id}/functions/bulk
Content-Type: application/json
X-Auth-Token: $TOKEN

{
  "items": [
    {
      "name": "前端门户",
      "category": "ILF",
      "complexity": "average",
      "ufp": 10,
      "us": 4.5,
      "source": "allocator",
      "description": "由 /cost-allocate 根据 P50 = X us 分摊"
    }
  ],
  "replace": false
}
```

**关键约束**：

- 每个模块产出**一条** FP（`category` 默认 `ILF` + `complexity` 默认 `average`，`ufp = 10` 对应 NESMA 表里 ILF average）
- `us` 字段必须用 allocator 返回的 `assigned_us`（**不要**用自己算的）
- `source = "allocator"`（不是 `claude_draft`；因为这条是数学分摊，不是 AI 抽取）
- `replace=false` 走追加，不覆盖用户已手填或 `claude_draft` 来源的 FP

---

## Step 7：完成后回复用户

> "已根据 P50 = X us 生成 N 条模块草稿，写入项目 {id}。请在浏览器审核：$BASE/projects/{id}/functions"

---

## 不要做的事

- 不要对正向（forward）项目跑分摊（Step 2 已守护）
- 不要绕过 allocator API 自己算 `assigned_us`
- 不要把 `source` 设成 `claude_draft`（前端会用不同颜色区分两类草稿）
- 不要 `replace=true` 覆盖用户已审核过的 FP
- 不要修改 `params_global`
