# 三个待完善功能补全 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补全全局审计聚合视图、项目批量导出/导入、采纳 FP 三个预留入口。

**Architecture:** 后端在现有 `audit` / `projects` / `functions` 三个 service + router 模块内新增端点与函数，复用既有的 `{success,data,error}` / `{ok,data}` 信封约定和 `_snapshot` 快照机制，不引入新表、不做 alembic migration。前端在对应 `api/*.ts` client 中新增方法，并改写 `AuditView.vue` 全局分支、`ProjectList.vue` 工具栏、`AiTaskPanel.vue` 采纳按钮三处占位 UI。三个功能相互独立，分三个 Phase 串行实施。

**Tech Stack:** FastAPI + SQLAlchemy + pytest（后端）；Vue 3 + TypeScript + Vitest（前端）。

---

## 文件结构

### 新建文件

| 文件 | 职责 |
|------|------|
| `server/tests/integration/test_v2_7_audit_global_api.py` | 全局审计端点集成测试 |
| `server/tests/integration/test_v2_7_projects_export_import_api.py` | 项目导出/导入 round-trip 集成测试 |
| `server/tests/integration/test_v2_7_accept_drafts_api.py` | 采纳 FP 端点集成测试 |
| `web/src/__tests__/views/AuditViewGlobal.test.ts` | `AuditView` global 分支单测 |
| `web/src/__tests__/api/projects-export-import.test.ts` | `projectsApi.exportProjects` / `importProjects` 单测 |
| `web/src/__tests__/ProjectListSelection.test.ts` | `ProjectList` 选择态 + 导入流程单测 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `server/app/services/audit.py` | 新增 `list_global()` |
| `server/app/api/audit.py` | 新增独立 router `GET /api/audit`，在 `main.py` 注册 |
| `server/app/main.py:18,109-118` | 注册全局 audit router |
| `server/app/schemas/audit.py` | 新增 `AuditGlobalOut`（带 `project_name`） |
| `server/app/schemas/project.py` | 新增 `ProjectExportRequest` / `ProjectBundle` / `ProjectImportResult` |
| `server/app/services/projects.py` | 新增 `export_projects()` / `import_bundle()` |
| `server/app/api/projects.py` | 新增 `POST /api/projects/export` 与 `POST /api/projects/import` |
| `server/app/services/functions.py` | 新增 `accept_drafts()` |
| `server/app/api/functions.py` | 新增 `POST /api/projects/{id}/functions/accept-drafts` |
| `web/src/api/audit.ts` | 新增 `auditApi.listGlobal()` + `GlobalAuditEntry` 类型 |
| `web/src/api/projects.ts` | 新增 `exportProjects()` / `importProjects()` + bundle 类型 |
| `web/src/api/functions.ts` | 新增 `acceptDrafts()` |
| `web/src/views/AuditView.vue` | global 分支改为真实时间线 + 项目名徽章 |
| `web/src/views/ProjectList.vue` | 表格视图加复选框列、导出/导入按钮逻辑 |
| `web/src/components/audit/AuditTimeline.vue` | 新增可选 `showProject` prop，渲染项目名徽章 |
| `web/src/components/fp/AiTaskPanel.vue` | 「采纳 FP」按钮启用 + 调 API + emit |
| `web/src/views/FpEditor.vue:526-529` | 接 `AiTaskPanel` 的 `accepted` 事件刷新 FP 列表 |

---

## Phase A — 全局审计聚合视图

### Task A1: 后端 audit service `list_global`

**Files:**
- Modify: `server/app/services/audit.py`（在文件末尾追加函数）
- Test: `server/tests/integration/test_v2_7_audit_global_api.py`（本 Task 仅建文件 + service 间接覆盖，端点测试见 A2）

- [ ] **Step 1: 写失败测试** —— 创建 `server/tests/integration/test_v2_7_audit_global_api.py`，内容：

```python
"""Integration tests for the global audit endpoint GET /api/audit (v2.7).

跨所有项目合并审计事件，按 ts/id 倒序，每条带 project_id + project_name。
"""

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


async def _make_project(c, name: str) -> str:
    r = await c.post("/api/projects", headers=H, json={
        "name": name, "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    return r.json()["data"]["id"]


async def test_global_audit_empty_db_returns_empty_list(client_factory):
    async with await client_factory() as client:
        r = await client.get("/api/audit", headers=H)
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["data"] == []
        assert body["error"] is None


async def test_global_audit_merges_events_across_projects(client_factory):
    async with await client_factory() as client:
        p1 = await _make_project(client, "项目甲")
        p2 = await _make_project(client, "项目乙")
        await client.patch(
            f"/api/projects/{p1}", headers={**H, "Content-Type": "application/json"},
            json={"name": "项目甲-改"})
        rows = (await client.get("/api/audit", headers=H)).json()["data"]
        pids = {r["project_id"] for r in rows}
        assert p1 in pids and p2 in pids
        names = {r["project_name"] for r in rows}
        assert "项目乙" in names
        # 倒序：相邻两条 id 单调递减
        ids = [r["id"] for r in rows]
        assert ids == sorted(ids, reverse=True)


async def test_global_audit_keyset_pagination(client_factory):
    async with await client_factory() as client:
        p1 = await _make_project(client, "P")
        for i in range(6):
            await client.patch(
                f"/api/projects/{p1}", headers={**H, "Content-Type": "application/json"},
                json={"name": f"P-{i}"})
        page1 = (await client.get("/api/audit?limit=3", headers=H)).json()["data"]
        assert len(page1) == 3
        last_id = page1[-1]["id"]
        page2 = (await client.get(
            f"/api/audit?limit=3&before_id={last_id}", headers=H)).json()["data"]
        assert all(r["id"] < last_id for r in page2)
```

- [ ] **Step 2: 跑测试确认失败** —— 命令：

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_7_audit_global_api.py -q
```

预期失败：3 个测试全部 FAIL，错误为 `assert 404 == 200`（`/api/audit` 路由未注册，命中 SPA fallback 或 404）。

- [ ] **Step 3: 写最小实现** —— 在 `server/app/services/audit.py` 文件末尾追加：

```python
def list_global(
    db: Session,
    limit: int = 100,
    before_id: int | None = None,
) -> list[tuple[AuditLog, str]]:
    """Return audit rows across ALL projects, newest first.

    与 list_for_project 同样的 keyset 分页语义（id < before_id 严格小于），
    区别是不按 project_id 过滤，并 join Project 取项目名。返回 (AuditLog,
    project_name) 元组列表 — router 层据此组装带 project_name 的响应。
    排序键用 (ts desc, id desc)：同一 ts 上多条事件靠 id 决定顺序，与
    keyset 游标 before_id 一致。
    """
    from ..db.models import Project

    q = (
        db.query(AuditLog, Project.name)
        .join(Project, AuditLog.project_id == Project.id)
    )
    if before_id is not None:
        q = q.filter(AuditLog.id < before_id)
    rows = (
        q.order_by(AuditLog.ts.desc(), AuditLog.id.desc())
        .limit(limit)
        .all()
    )
    return [(log, name) for log, name in rows]
```

- [ ] **Step 4: 跑测试确认通过** —— 命令同 Step 2。预期：service 已就位但端点仍未注册，3 个测试**仍 FAIL**（404）。这是预期中间态 —— 端点在 A2 注册。确认失败信息仍是 `404`（而非 service 层 `ImportError` / `AttributeError`），即 service 实现本身无语法错误。

- [ ] **Step 5: 提交** —— 命令：

```bash
cd server && git add app/services/audit.py tests/integration/test_v2_7_audit_global_api.py && git commit -m "feat(server): audit.list_global service + 全局审计端点集成测试"
```

---

### Task A2: 后端全局 audit 端点 + schema

**Files:**
- Modify: `server/app/schemas/audit.py`（追加 `AuditGlobalOut`）
- Modify: `server/app/api/audit.py`（新增 `global_router`）
- Modify: `server/app/main.py:18`（import）、`:109-118` 区段（include_router）
- Test: `server/tests/integration/test_v2_7_audit_global_api.py`（A1 已建）

- [ ] **Step 1: 写失败测试** —— 测试文件已在 A1 建好且当前为 FAIL（404），本 Task 不新增测试，直接让其转绿。无需改测试文件。

- [ ] **Step 2: 跑测试确认失败** —— 命令：

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_7_audit_global_api.py -q
```

预期失败：3 个测试 FAIL，`assert 404 == 200`。

- [ ] **Step 3: 写最小实现** ——

3a. 在 `server/app/schemas/audit.py` 文件末尾追加：

```python
class AuditGlobalOut(BaseModel):
    """全局审计条目 — 在 AuditOut 字段基础上附带项目名（跨项目时间线用）。"""

    id: int
    project_id: str
    project_name: str
    ts: datetime
    actor: str | None
    action: str
    target: str | None
    diff_json: str | None
```

3b. 改写 `server/app/api/audit.py` 为：

```python
"""审计日志只读查询接口。

- GET /api/projects/{project_id}/audit — 项目作用域时间线（v2.0 GAP-J）
- GET /api/audit                       — 全局跨项目聚合时间线（v2.7）

审计写入由 app/middleware/audit.py 在响应阶段隐式完成 — 本路由不负责写。

游标分页约定：客户端首次请求不带 before_id，拿到本页最小 id 后下次以
该 id 作 before_id 传入，服务端返回 id < before_id 的更早记录。limit
默认 100，上限 500。详见 services/audit.py。

鉴权由全局 X-Auth-Token 中间件（deps.py）统一拦截，本路由无需逐路由
Depends。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.audit import AuditGlobalOut, AuditOut
from ..services import audit as svc

router = APIRouter(prefix="/api/projects", tags=["audit"])
# 全局端点用独立 router，prefix 不能落在 /api/projects 下 —— 否则会被
# /{project_id}/audit 之外的项目级路由语义混淆，且 main.py 注册更清晰。
global_router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/{project_id}/audit")
def list_audit(
    project_id: str,
    limit: int = Query(100, ge=1, le=500),
    before_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
) -> dict:
    rows = svc.list_for_project(db, project_id, limit, before_id)
    return {
        "success": True,
        "data": [AuditOut.model_validate(r).model_dump(mode="json") for r in rows],
        "error": None,
    }


@global_router.get("/audit")
def list_audit_global(
    limit: int = Query(100, ge=1, le=500),
    before_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
) -> dict:
    pairs = svc.list_global(db, limit, before_id)
    data = [
        AuditGlobalOut(
            id=log.id,
            project_id=log.project_id,
            project_name=project_name,
            ts=log.ts,
            actor=log.actor,
            action=log.action,
            target=log.target,
            diff_json=log.diff_json,
        ).model_dump(mode="json")
        for log, project_name in pairs
    ]
    return {"success": True, "data": data, "error": None}
```

3c. 在 `server/app/main.py` 第 18 行 `from .api.audit import router as audit_router` 改为：

```python
from .api.audit import router as audit_router, global_router as audit_global_router
```

3d. 在 `server/app/main.py` 第 117 行 `app.include_router(audit_router)` 之后插入一行：

```python
    app.include_router(audit_router)
    app.include_router(audit_global_router)
```

- [ ] **Step 4: 跑测试确认通过** —— 命令：

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_7_audit_global_api.py -q
```

预期：3 passed。

- [ ] **Step 5: 提交** —— 命令：

```bash
cd server && git add app/schemas/audit.py app/api/audit.py app/main.py && git commit -m "feat(server): GET /api/audit 全局审计端点 + AuditGlobalOut schema"
```

---

### Task A3: 前端 audit client `listGlobal` + AuditTimeline 项目徽章

**Files:**
- Modify: `web/src/api/audit.ts`（新增 `GlobalAuditEntry` 类型 + `listGlobal`）
- Modify: `web/src/components/audit/AuditTimeline.vue`（新增 `showProject` prop）
- Test: `web/src/__tests__/api/projects-export-import.test.ts` —— 不涉及；本 Task 的 client 测试并入 A4 的 view 测试覆盖；这里仅做类型 + 组件改动，靠 `vue-tsc` + A4 测试守护。

- [ ] **Step 1: 写失败测试** —— 在 `web/src/__tests__/views/AuditViewGlobal.test.ts` 创建文件（A4 会扩充，这里先放最小用例驱动 `listGlobal` 类型存在）：

```typescript
import { describe, it, expect, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import AuditView from "@/views/AuditView.vue";

vi.mock("@/api/audit", () => ({
  auditApi: {
    list: vi.fn().mockResolvedValue([]),
    listGlobal: vi.fn().mockResolvedValue([]),
  },
}));
import { auditApi } from "@/api/audit";

const makeRouter = () =>
  createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/", component: { template: "<div/>" } }],
  });

describe("AuditView global 分支", () => {
  it("global=true 时调 auditApi.listGlobal", async () => {
    const router = makeRouter();
    await router.push("/");
    mount(AuditView, {
      props: { global: true },
      global: { plugins: [router] },
    });
    await flushPromises();
    expect(auditApi.listGlobal).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: 跑测试确认失败** —— 命令：

```bash
cd web && npx vitest run src/__tests__/views/AuditViewGlobal.test.ts
```

预期失败：`expected "listGlobal" to have been called` —— `AuditView.vue` 的 global 分支当前是占位卡，从不调 API。

- [ ] **Step 3: 写最小实现** ——

3a. 在 `web/src/api/audit.ts` 中，`AuditEntry` interface 之后新增类型，并在 `auditApi` 对象里新增 `listGlobal` 方法。完整改写后的 `web/src/api/audit.ts`：

```typescript
// v2.0 T8 — Project audit-log client surface.
// v2.7 — 新增全局审计 listGlobal（跨项目聚合）。
//
// Backend (server/app/api/audit.py) emits the new {success, data, error}
// envelope, so we go through api.raw and unwrap inline (same pattern as
// snapshots.ts — see that file for the rationale).
import { api, ApiError } from "./client";

export interface AuditEntry {
  id: number;
  project_id: string;
  ts: string;
  actor: string | null;
  action: string;
  target: string | null;
  diff_json: string | null;
}

// 全局审计条目 — 在 AuditEntry 基础上附带项目名。
export interface GlobalAuditEntry extends AuditEntry {
  project_name: string;
}

export interface AuditListOptions {
  limit?: number;
  beforeId?: number;
}

interface NewEnvelope<T> {
  success: boolean;
  data: T;
  error: { code: string; message?: string; details?: Record<string, unknown> } | null;
}

function unwrapNew<T>(payload: unknown): T {
  if (!payload || typeof payload !== "object") {
    throw new ApiError("INVALID_RESPONSE", "Server returned malformed envelope");
  }
  const env = payload as NewEnvelope<T>;
  if (env.success) return env.data;
  const e = env.error ?? { code: "UNKNOWN", message: "" };
  throw new ApiError(e.code, e.message ?? "", e.details);
}

function buildQs(opts: AuditListOptions): string {
  const params = new URLSearchParams();
  if (opts.limit !== undefined) params.set("limit", String(opts.limit));
  if (opts.beforeId !== undefined) params.set("before_id", String(opts.beforeId));
  const qs = params.toString();
  return qs ? "?" + qs : "";
}

export const auditApi = {
  async list(projectId: string, opts: AuditListOptions = {}): Promise<AuditEntry[]> {
    const url = `/api/projects/${projectId}/audit${buildQs(opts)}`;
    const resp = await api.raw.get<NewEnvelope<AuditEntry[]>>(url);
    return unwrapNew<AuditEntry[]>(resp.data);
  },

  async listGlobal(opts: AuditListOptions = {}): Promise<GlobalAuditEntry[]> {
    const url = `/api/audit${buildQs(opts)}`;
    const resp = await api.raw.get<NewEnvelope<GlobalAuditEntry[]>>(url);
    return unwrapNew<GlobalAuditEntry[]>(resp.data);
  },
};
```

3b. 在 `web/src/components/audit/AuditTimeline.vue` 的 `<script setup>` 中，把 `defineProps` 改为支持可选 `showProject`，并在模板的 `.tl-meta` 区块加项目名徽章。`defineProps` 行（第 4 行）改为：

```typescript
defineProps<{ events: AuditEntry[]; showProject?: boolean }>();
```

并把模板里 `.tl-meta` 区块（第 66-70 行）改为：

```html
        <div class="tl-meta">
          <span
            v-if="showProject && 'project_name' in e"
            class="badge badge-blue"
          >{{ (e as AuditEntry & { project_name?: string }).project_name }}</span>
          <span class="badge" :class="`badge-${typeOf(e) === 'ai' ? 'purple' : typeOf(e) === 'calc' ? 'blue' : ''}`">
            {{ e.action }}
          </span>
          <span class="muted">{{ e.actor ?? '系统' }}</span>
          <span class="muted mono" style="font-size: 11px">#{{ e.id }}</span>
        </div>
```

- [ ] **Step 4: 跑测试确认通过** —— 命令：

```bash
cd web && npx vitest run src/__tests__/views/AuditViewGlobal.test.ts && npx vue-tsc --noEmit
```

预期：vitest 中 `AuditView global 分支 > global=true 时调 auditApi.listGlobal` 这一条**仍 FAIL**（`AuditView.vue` 尚未改 global 分支，在 A4 完成）；`vue-tsc --noEmit` 必须 0 错误（client + 组件类型改动无误）。本 Task 验收点 = vue-tsc 通过。

- [ ] **Step 5: 提交** —— 命令：

```bash
cd web && git add src/api/audit.ts src/components/audit/AuditTimeline.vue src/__tests__/views/AuditViewGlobal.test.ts && git commit -m "feat(web): auditApi.listGlobal + AuditTimeline showProject 项目徽章"
```

---

### Task A4: 前端 AuditView global 分支接真实时间线

**Files:**
- Modify: `web/src/views/AuditView.vue`（全文改写）
- Test: `web/src/__tests__/views/AuditViewGlobal.test.ts`（A3 已建，本 Task 扩充）

- [ ] **Step 1: 写失败测试** —— 把 `web/src/__tests__/views/AuditViewGlobal.test.ts` 全文替换为：

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import AuditView from "@/views/AuditView.vue";

vi.mock("@/api/audit", () => ({
  auditApi: {
    list: vi.fn().mockResolvedValue([]),
    listGlobal: vi.fn(),
  },
}));
import { auditApi } from "@/api/audit";

const makeRouter = () =>
  createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/", component: { template: "<div/>" } }],
  });

const entry = (id: number, projectName: string) => ({
  id,
  project_id: `p-${id}`,
  project_name: projectName,
  ts: "2026-05-18T10:00:00Z",
  actor: "user",
  action: "project.update",
  target: null,
  diff_json: null,
});

const mountGlobal = async () => {
  const router = makeRouter();
  await router.push("/");
  return mount(AuditView, {
    props: { global: true },
    global: { plugins: [router] },
  });
};

describe("AuditView global 分支 (v2.7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("global=true 时调 auditApi.listGlobal 而非 list", async () => {
    (auditApi.listGlobal as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    await mountGlobal();
    await flushPromises();
    expect(auditApi.listGlobal).toHaveBeenCalled();
    expect(auditApi.list).not.toHaveBeenCalled();
  });

  it("渲染跨项目时间线并显示项目名徽章", async () => {
    (auditApi.listGlobal as ReturnType<typeof vi.fn>).mockResolvedValue([
      entry(2, "项目乙"),
      entry(1, "项目甲"),
    ]);
    const w = await mountGlobal();
    await flushPromises();
    expect(w.text()).toContain("项目甲");
    expect(w.text()).toContain("项目乙");
    expect(w.text()).not.toContain("将在 v2.3 上线");
  });

  it("满页时显示加载更多，点击后以最后一条 id 作游标续拉", async () => {
    const firstPage = Array.from({ length: 50 }, (_, i) => entry(100 - i, "P"));
    (auditApi.listGlobal as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce([entry(50, "P")]);
    const w = await mountGlobal();
    await flushPromises();
    const moreBtn = w.findAll("button").find((b) => b.text().includes("加载更多"));
    expect(moreBtn).toBeTruthy();
    await moreBtn!.trigger("click");
    await flushPromises();
    expect(auditApi.listGlobal).toHaveBeenLastCalledWith({ limit: 50, beforeId: 51 });
  });
});
```

- [ ] **Step 2: 跑测试确认失败** —— 命令：

```bash
cd web && npx vitest run src/__tests__/views/AuditViewGlobal.test.ts
```

预期失败：3 个测试全部 FAIL —— `auditApi.listGlobal` 从未被调用、占位文案 `将在 v2.3 上线` 仍存在、无「加载更多」按钮。

- [ ] **Step 3: 写最小实现** —— 把 `web/src/views/AuditView.vue` 全文替换为：

```vue
<script setup lang="ts">
// v2.2 T28 — AuditView：表格 → timeline，复用 AuditTimeline 组件。
// v2.7 — global 分支补全：调 auditApi.listGlobal 渲染跨项目聚合时间线。
import { ref, onMounted, computed } from "vue";
import { useRoute } from "vue-router";
import {
  auditApi,
  type AuditEntry,
  type GlobalAuditEntry,
} from "@/api/audit";
import AuditTimeline from "@/components/audit/AuditTimeline.vue";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";

const props = defineProps<{ global?: boolean }>();

const PAGE_SIZE = 50;

const route = useRoute();
const projectId = computed(() => {
  const id = route.params.id;
  return typeof id === "string" && id ? id : null;
});
const entries = ref<Array<AuditEntry | GlobalAuditEntry>>([]);
const loading = ref(false);
const hasMore = ref(true);

async function reload(beforeId?: number): Promise<void> {
  loading.value = true;
  try {
    let more: Array<AuditEntry | GlobalAuditEntry>;
    if (props.global) {
      more = await auditApi.listGlobal({ limit: PAGE_SIZE, beforeId });
    } else {
      if (!projectId.value) return;
      more = await auditApi.list(projectId.value, { limit: PAGE_SIZE, beforeId });
    }
    if (beforeId !== undefined) {
      entries.value = [...entries.value, ...more];
    } else {
      entries.value = more;
    }
    if (more.length < PAGE_SIZE) hasMore.value = false;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  if (props.global || projectId.value) void reload();
});

async function onLoadMore(): Promise<void> {
  const last = entries.value[entries.value.length - 1];
  if (last) await reload(last.id);
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title tight">
          {{ global ? '全局审计日志' : '项目审计' }}
        </h1>
        <div class="page-sub">
          <template v-if="global">{{ entries.length }} 条事件 · 跨项目聚合 · keyset 分页</template>
          <template v-else>{{ entries.length }} 条事件 · 不可变 append-only · keyset 分页</template>
        </div>
      </div>
    </div>

    <LoadingSkeleton v-if="loading && entries.length === 0" />
    <div
      v-else-if="entries.length === 0"
      class="card"
      style="padding: 40px; text-align: center; color: var(--text-3)"
    >
      暂无审计事件
    </div>
    <div v-else class="card" style="padding: 20px 24px">
      <AuditTimeline :events="entries" :show-project="global" />
      <div v-if="hasMore" style="margin-top: 20px; text-align: center">
        <button class="btn btn-ghost btn-sm" :disabled="loading" @click="onLoadMore">
          {{ loading ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 4: 跑测试确认通过** —— 命令：

```bash
cd web && npx vitest run src/__tests__/views/AuditViewGlobal.test.ts src/__tests__/AuditGlobalView.test.ts && npx vue-tsc --noEmit
```

预期：`AuditViewGlobal.test.ts` 3 passed。注意 `AuditGlobalView.test.ts`（A3 之前已存在）断言旧占位文案 `v2.3`，此时会 FAIL —— **本 Step 必须同步修复它**：把 `web/src/__tests__/AuditGlobalView.test.ts` 中的 mock 与断言更新为：

```typescript
import { describe, it, expect, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import AuditGlobalView from "@/views/AuditGlobalView.vue";

vi.mock("@/api/audit", () => ({
  auditApi: {
    list: vi.fn().mockResolvedValue([]),
    listGlobal: vi.fn().mockResolvedValue([]),
  },
}));

describe("AuditGlobalView", () => {
  it("mounts AuditView with global=true and renders 全局审计时间线", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/", component: { template: "<div/>" } }],
    });
    await router.push("/");
    const w = mount(AuditGlobalView, { global: { plugins: [router] } });
    await flushPromises();
    expect(w.text()).toContain("全局审计");
    expect(w.text()).not.toMatch(/将在 v2\.3 上线/);
  });
});
```

更新后重跑命令，预期：两个测试文件全部 passed，`vue-tsc --noEmit` 0 错误。

- [ ] **Step 5: 提交** —— 命令：

```bash
cd web && git add src/views/AuditView.vue src/__tests__/views/AuditViewGlobal.test.ts src/__tests__/AuditGlobalView.test.ts && git commit -m "feat(web): AuditView global 分支接真实跨项目审计时间线"
```

---

## Phase B — 项目批量导出 / 导入

### Task B1: 后端导出 / 导入 schema + service

**Files:**
- Modify: `server/app/schemas/project.py`（追加 bundle 相关 schema）
- Modify: `server/app/services/projects.py`（追加 `export_projects` / `import_bundle`）
- Test: `server/tests/integration/test_v2_7_projects_export_import_api.py`（B2 建文件，本 Task 仅 service，端点测试见 B2）

- [ ] **Step 1: 写失败测试** —— 创建 `server/tests/integration/test_v2_7_projects_export_import_api.py`，内容：

```python
"""Integration tests for POST /api/projects/export & /import (v2.7).

导出选定项目为 JSON bundle；导入同格式 bundle 总是新建项目。
round-trip 必须完整还原项目元数据 + FP + 参数 override，且生成新 id。
"""

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}
HJ = {**H, "Content-Type": "application/json"}


async def _make_project(c, name: str) -> str:
    r = await c.post("/api/projects", headers=H, json={
        "name": name, "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510", "client": "甲方A",
    })
    return r.json()["data"]["id"]


async def test_export_returns_bundle_with_core_fields(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client, "导出项目")
        r = await client.post("/api/projects/export", headers=HJ,
                               json={"ids": [pid]})
        assert r.status_code == 200
        bundle = r.json()["data"]
        assert bundle["version"] == "2.7"
        assert "exported_at" in bundle
        assert len(bundle["projects"]) == 1
        proj = bundle["projects"][0]
        assert proj["name"] == "导出项目"
        assert proj["client"] == "甲方A"
        assert "id" not in proj
        assert "function_points" in proj
        assert "param_overrides" in proj


async def test_export_skips_unknown_ids(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client, "存在的项目")
        r = await client.post("/api/projects/export", headers=HJ,
                               json={"ids": [pid, "no-such-id"]})
        assert r.status_code == 200
        assert len(r.json()["data"]["projects"]) == 1


async def test_export_all_unknown_ids_returns_empty(client_factory):
    async with await client_factory() as client:
        r = await client.post("/api/projects/export", headers=HJ,
                               json={"ids": ["x", "y"]})
        assert r.status_code == 200
        assert r.json()["data"]["projects"] == []


async def test_import_creates_new_projects_round_trip(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client, "原始项目")
        await client.post(f"/api/projects/{pid}/functions", headers=HJ,
                          json={"name": "fp1", "category": "EI",
                                "complexity": "low", "ufp": 3, "us": 3,
                                "source": "manual"})
        bundle = (await client.post("/api/projects/export", headers=HJ,
                                    json={"ids": [pid]})).json()["data"]
        r = await client.post("/api/projects/import", headers=HJ, json=bundle)
        assert r.status_code == 200
        result = r.json()["data"]
        assert result["imported"] == 1
        new_id = result["project_ids"][0]
        assert new_id != pid
        new = (await client.get(f"/api/projects/{new_id}", headers=H)).json()["data"]
        assert new["name"] == "原始项目"
        assert new["client"] == "甲方A"
        fps = (await client.get(f"/api/projects/{new_id}/functions",
                                headers=H)).json()["data"]
        assert len(fps) == 1
        assert fps[0]["name"] == "fp1"


async def test_import_rejects_malformed_bundle(client_factory):
    async with await client_factory() as client:
        r = await client.post("/api/projects/import", headers=HJ,
                               json={"version": "2.7"})  # 缺 projects
        assert r.status_code == 400


async def test_import_rejects_project_missing_required_field(client_factory):
    async with await client_factory() as client:
        bad = {"version": "2.7", "exported_at": "2026-05-18T00:00:00Z",
               "projects": [{"name": "缺字段"}]}  # 缺 project_type 等
        r = await client.post("/api/projects/import", headers=HJ, json=bad)
        assert r.status_code == 400
```

- [ ] **Step 2: 跑测试确认失败** —— 命令：

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_7_projects_export_import_api.py -q
```

预期失败：6 个测试全部 FAIL，`assert 404 == 200` / `assert 404 == 400`（端点未注册）。

- [ ] **Step 3: 写最小实现** ——

3a. 在 `server/app/schemas/project.py` 文件末尾追加（注意 `FunctionPointBase` 从 functions schema import）：

```python
from .functions import FunctionPointBase


class ParamOverrideItem(BaseModel):
    key: str
    value: str
    reason: Optional[str] = None


class ProjectBundleItem(BaseModel):
    """单个项目的可移植快照 — 不含运行时与历史数据。"""

    name: str = Field(min_length=1, max_length=NAME_MAX)
    project_type: Literal["dev_only", "ops_only", "dev_and_ops"]
    phase: Literal["budget", "bidding", "planning", "change", "settled"]
    city: str
    industry: str
    client: Optional[str] = None
    evaluator: Optional[str] = None
    mode: Literal["forward", "reverse"]
    target_cost: Optional[float] = None
    other_cost: float = 0
    include_ops: bool = False
    alpha_dev: float = 1.0
    fp_method: Literal["nesma_estimated", "ifpug", "quick"] = "nesma_estimated"
    basis_data_ver: str
    factors_dev: Optional[dict] = None
    factors_ops: Optional[dict] = None
    param_overrides: list[ParamOverrideItem] = Field(default_factory=list)
    function_points: list[FunctionPointBase] = Field(default_factory=list)


class ProjectBundle(BaseModel):
    """导出 / 导入的 JSON bundle 顶层结构。"""

    version: str
    exported_at: str
    projects: list[ProjectBundleItem]


class ProjectExportRequest(BaseModel):
    ids: list[str]


class ProjectImportResult(BaseModel):
    imported: int
    project_ids: list[str]
```

3b. 在 `server/app/services/projects.py` 文件末尾追加（顶部 import 区已有 `json` / `uuid` / `datetime, timezone`）：

```python
BUNDLE_VERSION = "2.7"


def export_projects(db: Session, ids: list[str]) -> dict:
    """把指定项目导出为可移植 bundle dict。

    不存在的 id 静默跳过；全部不存在则 projects 为空数组。bundle 只含
    可移植数据 — 不含 id / created_at / updated_at / results / snapshots /
    uploads / ai_tasks / audit_log（运行时与历史数据）。
    """
    projects_out: list[dict] = []
    for pid in ids:
        p = db.query(ProjectORM).filter_by(id=pid).first()
        if not p:
            continue
        fps = [
            {
                "subsystem": fp.subsystem,
                "l1_module": fp.l1_module,
                "l2_module": fp.l2_module,
                "description": fp.description,
                "name": fp.name,
                "category": fp.category,
                "complexity": fp.complexity,
                "fp_kind": fp.fp_kind,
                "ufp": fp.ufp,
                "reuse_level": fp.reuse_level,
                "modify_type": fp.modify_type,
                "us": fp.us,
                "source": fp.source,
                "locked": fp.locked,
                "notes": fp.notes,
                "ord": fp.ord,
            }
            for fp in p.function_points
        ]
        overrides = [
            {"key": po.key, "value": po.value, "reason": po.reason}
            for po in p.param_overrides
        ]
        projects_out.append({
            "name": p.name,
            "project_type": p.project_type,
            "phase": p.phase,
            "city": p.city,
            "industry": p.industry,
            "client": p.client,
            "evaluator": p.evaluator,
            "mode": p.mode,
            "target_cost": p.target_cost,
            "other_cost": p.other_cost,
            "include_ops": p.include_ops,
            "alpha_dev": p.alpha_dev,
            "fp_method": p.fp_method,
            "basis_data_ver": p.basis_data_ver,
            "factors_dev": json.loads(p.factors_dev_json) if p.factors_dev_json else None,
            "factors_ops": json.loads(p.factors_ops_json) if p.factors_ops_json else None,
            "param_overrides": overrides,
            "function_points": fps,
        })
    return {
        "version": BUNDLE_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "projects": projects_out,
    }


def import_bundle(db: Session, bundle) -> tuple[int, list[str]]:
    """把已校验的 ProjectBundle 落库为新建项目。

    bundle 形参是 schemas.project.ProjectBundle 实例（router 层用 Pydantic
    校验后传入，格式非法在 router 层就被拒为 400）。每个项目生成新 id，
    不覆盖、不合并、不按名匹配 —— 落库逻辑参照 copy_project。
    返回 (导入数量, 新项目 id 列表)。
    """
    new_ids: list[str] = []
    for item in bundle.projects:
        new_id = f"prj-{uuid.uuid4().hex[:12]}"
        new = ProjectORM(
            id=new_id,
            name=item.name,
            project_type=item.project_type,
            phase=item.phase,
            city=item.city,
            industry=item.industry,
            client=item.client,
            evaluator=item.evaluator,
            mode=item.mode,
            target_cost=item.target_cost,
            other_cost=item.other_cost,
            include_ops=item.include_ops,
            alpha_dev=item.alpha_dev,
            fp_method=item.fp_method,
            basis_data_ver=item.basis_data_ver,
            factors_dev_json=json.dumps(item.factors_dev) if item.factors_dev is not None else None,
            factors_ops_json=json.dumps(item.factors_ops) if item.factors_ops is not None else None,
        )
        db.add(new)
        for fp in item.function_points:
            db.add(FunctionPoint(
                id=f"fp-{uuid.uuid4().hex[:12]}",
                project_id=new_id,
                version=1,
                **fp.model_dump(),
            ))
        for po in item.param_overrides:
            db.add(ParamOverride(
                project_id=new_id,
                key=po.key,
                value=po.value,
                reason=po.reason,
            ))
        new_ids.append(new_id)
    db.commit()
    return len(new_ids), new_ids
```

- [ ] **Step 4: 跑测试确认通过** —— 命令同 Step 2。预期：6 个测试**仍 FAIL**（404 / 400 路由未注册）—— 端点在 B2 注册。确认失败信息仍是 `404` / `400` 来自路由缺失而非 service `ImportError`。可用以下命令单独验证 service 无语法错误：

```bash
cd server && .venv/bin/python -c "from app.services.projects import export_projects, import_bundle; from app.schemas.project import ProjectBundle, ProjectExportRequest; print('ok')"
```

预期输出 `ok`。

- [ ] **Step 5: 提交** —— 命令：

```bash
cd server && git add app/schemas/project.py app/services/projects.py tests/integration/test_v2_7_projects_export_import_api.py && git commit -m "feat(server): 项目导出/导入 bundle schema + service"
```

---

### Task B2: 后端导出 / 导入端点

**Files:**
- Modify: `server/app/api/projects.py`（新增两个端点）
- Test: `server/tests/integration/test_v2_7_projects_export_import_api.py`（B1 已建）

- [ ] **Step 1: 写失败测试** —— 测试文件已在 B1 建好且当前 FAIL，本 Task 不新增测试。

- [ ] **Step 2: 跑测试确认失败** —— 命令：

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_7_projects_export_import_api.py -q
```

预期失败：6 个测试 FAIL（404 / 400）。

- [ ] **Step 3: 写最小实现** —— 在 `server/app/api/projects.py` 中：

3a. 把第 6 行 import 改为：

```python
from ..schemas.project import (ProjectCreate, ProjectRead, ProjectPatch, ProjectStats,
                                 ProjectBundle, ProjectExportRequest, ProjectImportResult)
```

3b. 在文件末尾（`copy` 端点之后）追加两个端点。注意 `export` / `import` 必须放在 `get_one`（`/{project_id}`）之前**还是之后**？FastAPI 按声明顺序匹配，`/export` 与 `/import` 是静态段，`/{project_id}` 是动态段 —— 静态段优先匹配，但保险起见放在 `get_one` 之前。**实施时把以下两个端点函数插入到 `server/app/api/projects.py` 第 69 行（`get_one` 定义之前、`get_project_stats` 之后）：**

```python
@router.post("/export")
def export_projects(payload: ProjectExportRequest, db: Session = Depends(get_db)) -> dict:
    bundle = svc.export_projects(db, payload.ids)
    return {"success": True, "data": bundle, "error": None}


@router.post("/import")
def import_projects(payload: ProjectBundle, db: Session = Depends(get_db)) -> dict:
    n, ids = svc.import_bundle(db, payload)
    result = ProjectImportResult(imported=n, project_ids=ids)
    return {"success": True, "data": result.model_dump(mode="json"), "error": None}
```

> 说明：`import` 端点的 body 直接用 `ProjectBundle` 做参数类型 —— bundle 格式非法（缺 `projects`、项目缺必填字段）时 FastAPI 自动返回 422。但 spec 要求 **400**。因此把端点改为接收原始 dict 后手动校验：

把上面的 `import_projects` 替换为：

```python
@router.post("/import")
def import_projects(payload: dict, db: Session = Depends(get_db)) -> dict:
    from pydantic import ValidationError
    try:
        bundle = ProjectBundle.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(
            400,
            detail={"error": {
                "code": "INVALID_BUNDLE",
                "message": "导入数据格式非法",
                "problem": str(e.errors()[0].get("msg", "格式校验失败")),
            }},
        )
    n, ids = svc.import_bundle(db, bundle)
    result = ProjectImportResult(imported=n, project_ids=ids)
    return {"success": True, "data": result.model_dump(mode="json"), "error": None}
```

- [ ] **Step 4: 跑测试确认通过** —— 命令：

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_7_projects_export_import_api.py -q
```

预期：6 passed。

- [ ] **Step 5: 提交** —— 命令：

```bash
cd server && git add app/api/projects.py && git commit -m "feat(server): POST /api/projects/export 与 /import 端点"
```

---

### Task B3: 前端 projects client 导出 / 导入方法

**Files:**
- Modify: `web/src/api/projects.ts`（新增类型 + 两个方法）
- Test: `web/src/__tests__/api/projects-export-import.test.ts`（新建）

- [ ] **Step 1: 写失败测试** —— 创建 `web/src/__tests__/api/projects-export-import.test.ts`：

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  api: {
    raw: { post: vi.fn() },
  },
  ApiError: class ApiError extends Error {},
}));

import { projectsApi } from "@/api/projects";
import { api } from "@/api/client";

describe("projectsApi 导出/导入 (v2.7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("exportProjects 调 POST /api/projects/export 并返回 bundle", async () => {
    const bundle = { version: "2.7", exported_at: "x", projects: [] };
    (api.raw.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { success: true, data: bundle, error: null },
    });
    const result = await projectsApi.exportProjects(["p-1", "p-2"]);
    expect(api.raw.post).toHaveBeenCalledWith("/api/projects/export", {
      ids: ["p-1", "p-2"],
    });
    expect(result).toEqual(bundle);
  });

  it("importProjects 调 POST /api/projects/import 并返回结果", async () => {
    const bundle = { version: "2.7", exported_at: "x", projects: [] };
    (api.raw.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        success: true,
        data: { imported: 2, project_ids: ["n-1", "n-2"] },
        error: null,
      },
    });
    const result = await projectsApi.importProjects(bundle);
    expect(api.raw.post).toHaveBeenCalledWith("/api/projects/import", bundle);
    expect(result).toEqual({ imported: 2, project_ids: ["n-1", "n-2"] });
  });

  it("importProjects 在 success=false 时抛 ApiError", async () => {
    (api.raw.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        success: false,
        data: null,
        error: { code: "INVALID_BUNDLE", message: "格式非法" },
      },
    });
    await expect(
      projectsApi.importProjects({ version: "2.7", exported_at: "x", projects: [] }),
    ).rejects.toThrow();
  });
});
```

- [ ] **Step 2: 跑测试确认失败** —— 命令：

```bash
cd web && npx vitest run src/__tests__/api/projects-export-import.test.ts
```

预期失败：`projectsApi.exportProjects is not a function`。

- [ ] **Step 3: 写最小实现** —— 在 `web/src/api/projects.ts` 中：

3a. 在 `ProjectQueryResult` interface 之后（第 54 行后）追加 bundle 类型：

```typescript
// v2.7 — 项目批量导出 / 导入 bundle 类型。
export interface ProjectBundleItem {
  name: string;
  project_type: ProjectType;
  phase: ProjectPhase;
  city: string;
  industry: string;
  client?: string | null;
  evaluator?: string | null;
  mode: ProjectMode;
  target_cost?: number | null;
  other_cost?: number;
  include_ops?: boolean;
  alpha_dev?: number;
  fp_method?: "nesma_estimated" | "ifpug" | "quick";
  basis_data_ver: string;
  factors_dev?: Record<string, unknown> | null;
  factors_ops?: Record<string, unknown> | null;
  param_overrides: Array<{ key: string; value: string; reason?: string | null }>;
  function_points: Array<Record<string, unknown>>;
}

export interface ProjectBundle {
  version: string;
  exported_at: string;
  projects: ProjectBundleItem[];
}

export interface ProjectImportResult {
  imported: number;
  project_ids: string[];
}
```

3b. 在 `projectsApi` 对象内，`copy` 方法之后（第 121 行 `},` 之后、第 122 行 `};` 之前）追加：

```typescript
  async exportProjects(ids: string[]): Promise<ProjectBundle> {
    const resp = await api.raw.post<NewEnvelope<ProjectBundle>>(
      "/api/projects/export",
      { ids },
    );
    return unwrapNew<ProjectBundle>(resp.data);
  },

  async importProjects(bundle: ProjectBundle): Promise<ProjectImportResult> {
    const resp = await api.raw.post<NewEnvelope<ProjectImportResult>>(
      "/api/projects/import",
      bundle,
    );
    return unwrapNew<ProjectImportResult>(resp.data);
  },
```

- [ ] **Step 4: 跑测试确认通过** —— 命令：

```bash
cd web && npx vitest run src/__tests__/api/projects-export-import.test.ts && npx vue-tsc --noEmit
```

预期：3 passed，`vue-tsc --noEmit` 0 错误。

- [ ] **Step 5: 提交** —— 命令：

```bash
cd web && git add src/api/projects.ts src/__tests__/api/projects-export-import.test.ts && git commit -m "feat(web): projectsApi.exportProjects / importProjects + bundle 类型"
```

---

### Task B4: 前端 ProjectList 复选框 + 导出 / 导入交互

**Files:**
- Modify: `web/src/views/ProjectList.vue`（加复选框列、`selectedIds`、导出/导入逻辑）
- Test: `web/src/__tests__/ProjectListSelection.test.ts`（新建）

- [ ] **Step 1: 写失败测试** —— 创建 `web/src/__tests__/ProjectListSelection.test.ts`：

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import ProjectList from "@/views/ProjectList.vue";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    query: vi.fn(),
    exportProjects: vi.fn(),
    importProjects: vi.fn(),
  },
}));
vi.mock("@/api/stats", () => ({
  statsApi: { getProjectStats: vi.fn().mockResolvedValue(null) },
}));

import { projectsApi } from "@/api/projects";

const mkProject = (id: string, name: string) => ({
  id,
  name,
  project_type: "dev_only",
  mode: "forward",
  city: "北京",
  industry: "电子政务",
  phase: "bidding",
  basis_data_ver: "CSBMK®-202510",
  created_at: "2026-05-18T00:00:00Z",
  updated_at: "2026-05-18T00:00:00Z",
});

const makeRouter = () =>
  createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: { template: "<div/>" } },
      { path: "/projects/:id/functions", component: { template: "<div/>" }, name: "fp-editor" },
      { path: "/projects/new", component: { template: "<div/>" }, name: "project-wizard" },
    ],
  });

const mountList = async () => {
  const router = makeRouter();
  await router.push("/");
  const w = mount(ProjectList, { global: { plugins: [router] } });
  await flushPromises();
  return w;
};

describe("ProjectList 选择态 + 导出导入 (v2.7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (projectsApi.query as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [mkProject("p-1", "项目甲"), mkProject("p-2", "项目乙")],
      meta: { total: 2, page: 1, size: 50 },
    });
  });

  it("表格视图每行有复选框，表头有全选", async () => {
    const w = await mountList();
    expect(w.find('[data-testid="select-all"]').exists()).toBe(true);
    expect(w.findAll('[data-testid="row-checkbox"]').length).toBe(2);
  });

  it("未选中任何项目时批量导出按钮 disabled", async () => {
    const w = await mountList();
    const exportBtn = w.find('[data-testid="export-btn"]');
    expect((exportBtn.element as HTMLButtonElement).disabled).toBe(true);
  });

  it("勾选单行后批量导出可点并调 exportProjects", async () => {
    (projectsApi.exportProjects as ReturnType<typeof vi.fn>).mockResolvedValue({
      version: "2.7",
      exported_at: "x",
      projects: [],
    });
    const w = await mountList();
    await w.findAll('[data-testid="row-checkbox"]')[0].setValue(true);
    const exportBtn = w.find('[data-testid="export-btn"]');
    expect((exportBtn.element as HTMLButtonElement).disabled).toBe(false);
    await exportBtn.trigger("click");
    await flushPromises();
    expect(projectsApi.exportProjects).toHaveBeenCalledWith(["p-1"]);
  });

  it("全选勾选后选中所有项目", async () => {
    const w = await mountList();
    await w.find('[data-testid="select-all"]').setValue(true);
    const exportBtn = w.find('[data-testid="export-btn"]');
    expect((exportBtn.element as HTMLButtonElement).disabled).toBe(false);
  });

  it("导入文件后调 importProjects 并重新加载列表", async () => {
    (projectsApi.importProjects as ReturnType<typeof vi.fn>).mockResolvedValue({
      imported: 1,
      project_ids: ["n-1"],
    });
    const w = await mountList();
    const bundle = { version: "2.7", exported_at: "x", projects: [] };
    const file = new File([JSON.stringify(bundle)], "import.json", {
      type: "application/json",
    });
    const input = w.find('[data-testid="import-input"]');
    Object.defineProperty(input.element, "files", { value: [file] });
    await input.trigger("change");
    await flushPromises();
    expect(projectsApi.importProjects).toHaveBeenCalledWith(bundle);
    // 导入后重新 query：初次 onMounted 1 次 + 导入后 1 次
    expect((projectsApi.query as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThanOrEqual(2);
  });
});
```

- [ ] **Step 2: 跑测试确认失败** —— 命令：

```bash
cd web && npx vitest run src/__tests__/ProjectListSelection.test.ts
```

预期失败：5 个测试全部 FAIL —— `[data-testid="select-all"]` / `row-checkbox` / `export-btn` / `import-input` 均不存在。

- [ ] **Step 3: 写最小实现** —— 在 `web/src/views/ProjectList.vue` 中做四处改动：

3a. `<script setup>` 中，在 `const view = ref(...)` 行（第 44 行）之后追加状态与逻辑：

```typescript
// v2.7 — 批量导出 / 导入
const selectedIds = ref<Set<string>>(new Set());
const fileInput = ref<HTMLInputElement | null>(null);
const importHint = ref<string>("");

const allSelected = computed(
  () =>
    filtered.value.length > 0 &&
    filtered.value.every((p) => selectedIds.value.has(p.id)),
);

function toggleRow(id: string, checked: boolean): void {
  const next = new Set(selectedIds.value);
  if (checked) next.add(id);
  else next.delete(id);
  selectedIds.value = next;
}

function toggleAll(checked: boolean): void {
  if (checked) {
    selectedIds.value = new Set(filtered.value.map((p) => p.id));
  } else {
    selectedIds.value = new Set();
  }
}

async function onExport(): Promise<void> {
  if (selectedIds.value.size === 0) {
    if (view.value === "card") {
      importHint.value = "请切换到表格视图勾选项目";
    }
    return;
  }
  try {
    const bundle = await projectsApi.exportProjects([...selectedIds.value]);
    const blob = new Blob([JSON.stringify(bundle, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, "");
    a.href = url;
    a.download = `projects-export-${today}.json`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    importHint.value = e instanceof ApiError ? e.message : "导出失败";
  }
}

function triggerImport(): void {
  fileInput.value?.click();
}

async function onImportFile(ev: Event): Promise<void> {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  importHint.value = "";
  try {
    const text = await file.text();
    const bundle = JSON.parse(text);
    const result = await projectsApi.importProjects(bundle);
    importHint.value = `已导入 ${result.imported} 个项目`;
    await load();
  } catch (e) {
    importHint.value =
      e instanceof ApiError ? `导入失败：${e.message}` : "导入失败：文件格式非法";
  } finally {
    input.value = "";
  }
}
```

> 说明：`onExport` 在卡片视图下若无选中给出提示文案，符合 spec「卡片视图不加复选框；该视图下批量导出点击时提示请切换到表格视图」。

3b. 模板工具栏（第 157-158 行的两个 `<button>`）替换为：

```html
      <button
        type="button"
        class="btn btn-ghost"
        data-testid="import-btn"
        @click="triggerImport"
      >导入</button>
      <button
        type="button"
        class="btn btn-ghost"
        data-testid="export-btn"
        :disabled="selectedIds.size === 0"
        @click="onExport"
      >批量导出（{{ selectedIds.size }}）</button>
      <input
        ref="fileInput"
        type="file"
        accept=".json"
        data-testid="import-input"
        hidden
        @change="onImportFile"
      >
```

3c. 在 `<ProjectFilterBar ... />` 之后（第 178 行 `/>` 之后）插入导入提示横幅：

```html
    <div
      v-if="importHint"
      class="banner"
      :class="importHint.includes('失败') ? 'banner-amber' : 'banner-green'"
      style="margin-top: 4px"
    >
      {{ importHint }}
    </div>
```

3d. 表格 `<thead>` 与 `<tbody>` 加复选框列。把表格 `<thead><tr>`（第 207-217 行）首行 `<th>项目名 / 编码</th>` 之前插入：

```html
            <th style="width: 36px">
              <input
                type="checkbox"
                data-testid="select-all"
                :checked="allSelected"
                @change="toggleAll(($event.target as HTMLInputElement).checked)"
              >
            </th>
```

并在 `<tbody>` 的 `<tr ...>` 内、`<td>` 项目名单元格（第 227 行 `<td>`）之前插入：

```html
            <td style="width: 36px" @click.stop>
              <input
                type="checkbox"
                data-testid="row-checkbox"
                :checked="selectedIds.has(p.id)"
                @change="toggleRow(p.id, ($event.target as HTMLInputElement).checked)"
              >
            </td>
```

- [ ] **Step 4: 跑测试确认通过** —— 命令：

```bash
cd web && npx vitest run src/__tests__/ProjectListSelection.test.ts && npx vue-tsc --noEmit
```

预期：5 passed，`vue-tsc --noEmit` 0 错误。

- [ ] **Step 5: 提交** —— 命令：

```bash
cd web && git add src/views/ProjectList.vue src/__tests__/ProjectListSelection.test.ts && git commit -m "feat(web): ProjectList 复选框选择 + 批量导出/导入交互"
```

---

## Phase C — 采纳 FP（批量确认 AI 草稿）

### Task C1: 后端 accept-drafts service + 端点

**Files:**
- Modify: `server/app/services/functions.py`（新增 `accept_drafts`）
- Modify: `server/app/api/functions.py`（新增 `POST /accept-drafts` 端点）
- Test: `server/tests/integration/test_v2_7_accept_drafts_api.py`（新建）

- [ ] **Step 1: 写失败测试** —— 创建 `server/tests/integration/test_v2_7_accept_drafts_api.py`：

```python
"""Integration tests for POST /api/projects/{id}/functions/accept-drafts (v2.7).

把项目内所有 source='claude_draft' 的功能点改为 source='ai_extracted'
（脱离草稿高亮），改动前存一次 FP 快照（reason=accept_drafts）。
"""

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}
HJ = {**H, "Content-Type": "application/json"}


async def _make_project(c) -> str:
    r = await c.post("/api/projects", headers=H, json={
        "name": "T", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    return r.json()["data"]["id"]


async def _add_fp(c, pid: str, name: str, source: str) -> None:
    await c.post(f"/api/projects/{pid}/functions", headers=HJ,
                 json={"name": name, "category": "EI", "complexity": "low",
                       "ufp": 3, "us": 3, "source": source})


async def test_accept_drafts_promotes_claude_draft_to_ai_extracted(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        await _add_fp(client, pid, "草稿1", "claude_draft")
        await _add_fp(client, pid, "草稿2", "claude_draft")
        await _add_fp(client, pid, "手工", "manual")
        r = await client.post(
            f"/api/projects/{pid}/functions/accept-drafts", headers=HJ)
        assert r.status_code == 200
        assert r.json()["data"]["accepted"] == 2
        fps = (await client.get(
            f"/api/projects/{pid}/functions", headers=H)).json()["data"]
        by_name = {f["name"]: f["source"] for f in fps}
        assert by_name["草稿1"] == "ai_extracted"
        assert by_name["草稿2"] == "ai_extracted"
        assert by_name["手工"] == "manual"


async def test_accept_drafts_creates_snapshot(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        await _add_fp(client, pid, "草稿1", "claude_draft")
        await client.post(
            f"/api/projects/{pid}/functions/accept-drafts", headers=HJ)
        snaps = (await client.get(
            f"/api/projects/{pid}/functions/snapshots", headers=H)).json()["data"]
        assert any(s["reason"] == "accept_drafts" for s in snaps)


async def test_accept_drafts_no_drafts_returns_zero(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        await _add_fp(client, pid, "手工", "manual")
        r = await client.post(
            f"/api/projects/{pid}/functions/accept-drafts", headers=HJ)
        assert r.status_code == 200
        assert r.json()["data"]["accepted"] == 0


async def test_accept_drafts_404_on_unknown_project(client_factory):
    async with await client_factory() as client:
        r = await client.post(
            "/api/projects/no-such-id/functions/accept-drafts", headers=HJ)
        assert r.status_code == 404
```

- [ ] **Step 2: 跑测试确认失败** —— 命令：

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_7_accept_drafts_api.py -q
```

预期失败：4 个测试全部 FAIL，`assert 404 == 200` / `405`（端点未注册）。

- [ ] **Step 3: 写最小实现** ——

3a. 在 `server/app/services/functions.py` 文件末尾追加：

```python
def accept_drafts(db: Session, project_id: str) -> int:
    """把项目内所有 source='claude_draft' 的功能点采纳为 'ai_extracted'。

    改动前先存一次 FP 快照（reason='accept_drafts'）便于回退 —— 快照版本用
    当前最大 version，与 bulk_write 的 pre-replace 快照同一约定，避免与
    UNIQUE(project_id, version) 冲突时跳过重复写。
    项目不存在抛 PROJECT_NOT_FOUND；无 claude_draft 行时返回 0（非错误，
    且不写快照 —— 无改动无需快照）。
    """
    if not db.query(Project).filter_by(id=project_id).first():
        raise ValueError("PROJECT_NOT_FOUND")

    drafts = (
        db.query(FunctionPoint)
        .filter_by(project_id=project_id, source="claude_draft")
        .all()
    )
    if not drafts:
        return 0

    current_max = (
        db.query(func.max(FunctionPoint.version))
        .filter_by(project_id=project_id)
        .scalar()
    )
    if current_max is not None:
        existing_snap = (
            db.query(FPSnapshot)
            .filter_by(project_id=project_id, version=current_max)
            .first()
        )
        if not existing_snap:
            _snapshot(db, project_id, current_max, reason="accept_drafts")

    for fp in drafts:
        fp.source = "ai_extracted"
    db.commit()
    _mark_results_stale(db, project_id)
    return len(drafts)
```

3b. 在 `server/app/api/functions.py` 中，`bulk` 端点之后（第 58 行 `}` 之后、第 60 行 `@router.get("/snapshots")` 之前）插入：

```python
@router.post("/accept-drafts")
def accept_drafts(project_id: str, db: Session = Depends(get_db)):
    try:
        n = svc.accept_drafts(db, project_id)
    except ValueError as e:
        raise HTTPException(404, detail={"error": {"code": str(e)}})
    return {"ok": True, "data": {"accepted": n}}
```

- [ ] **Step 4: 跑测试确认通过** —— 命令：

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_7_accept_drafts_api.py -q
```

预期：4 passed。

- [ ] **Step 5: 提交** —— 命令：

```bash
cd server && git add app/services/functions.py app/api/functions.py tests/integration/test_v2_7_accept_drafts_api.py && git commit -m "feat(server): accept-drafts 端点 — claude_draft → ai_extracted + 快照"
```

---

### Task C2: 前端 functions client `acceptDrafts`

**Files:**
- Modify: `web/src/api/functions.ts`（新增 `acceptDrafts`）
- Test: `web/src/__tests__/api/functions.test.ts`（在现有文件追加用例）

- [ ] **Step 1: 写失败测试** —— 先查看 `web/src/__tests__/api/functions.test.ts` 现有 mock 结构（顶部 `vi.mock("@/api/client", ...)`），在该文件 `describe` 块末尾（最后一个 `it(...)` 之后、`describe` 闭合 `});` 之前）追加用例：

```typescript
  it("acceptDrafts 调 POST /api/projects/:id/functions/accept-drafts", async () => {
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      accepted: 3,
    });
    const result = await functionsApi.acceptDrafts("p-1");
    expect(api.post).toHaveBeenCalledWith(
      "/api/projects/p-1/functions/accept-drafts",
    );
    expect(result).toEqual({ accepted: 3 });
  });
```

> 实施时若 `functions.test.ts` 的 mock 未包含 `post`，需把顶部 `vi.mock("@/api/client", ...)` 的 `api` 对象补上 `post: vi.fn()`。先读该文件确认。

- [ ] **Step 2: 跑测试确认失败** —— 命令：

```bash
cd web && npx vitest run src/__tests__/api/functions.test.ts
```

预期失败：`functionsApi.acceptDrafts is not a function`。

- [ ] **Step 3: 写最小实现** —— 在 `web/src/api/functions.ts` 的 `functionsApi` 对象内，`restore` 方法之后（第 61 行 `),` 之后、第 62 行 `};` 之前）追加：

```typescript
  acceptDrafts: (projectId: string) =>
    api.post<{ accepted: number }>(
      `/api/projects/${projectId}/functions/accept-drafts`,
    ),
```

- [ ] **Step 4: 跑测试确认通过** —— 命令：

```bash
cd web && npx vitest run src/__tests__/api/functions.test.ts && npx vue-tsc --noEmit
```

预期：全部 passed（含新增 acceptDrafts 用例），`vue-tsc --noEmit` 0 错误。

- [ ] **Step 5: 提交** —— 命令：

```bash
cd web && git add src/api/functions.ts src/__tests__/api/functions.test.ts && git commit -m "feat(web): functionsApi.acceptDrafts"
```

---

### Task C3: 前端 AiTaskPanel 采纳按钮 + FpEditor 刷新

**Files:**
- Modify: `web/src/components/fp/AiTaskPanel.vue`（按钮启用 + 调 API + emit）
- Modify: `web/src/views/FpEditor.vue:526-529`（接 `accepted` 事件刷新 FP）
- Test: `web/src/__tests__/AiTaskPanel.test.ts`（追加用例）

- [ ] **Step 1: 写失败测试** —— 在 `web/src/__tests__/AiTaskPanel.test.ts` 中：

1a. 把顶部 `vi.mock("@/api/aiTasks", ...)` 之后追加对 functions API 的 mock，并 import：

```typescript
vi.mock("@/api/functions", () => ({
  functionsApi: {
    acceptDrafts: vi.fn(),
  },
}));
import { functionsApi } from "@/api/functions";
```

1b. 在 `describe("AiTaskPanel (v2.5)", ...)` 块末尾（最后一个 `it` 之后）追加用例：

```typescript
  it("task 为 done 时采纳 FP 按钮可点", async () => {
    (aiTasksApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([
      mockTask({ status: "done", progress_pct: 100 }),
    ]);
    const w = mount(AiTaskPanel, { props: { open: true, projectId: "p-1" } });
    await flushPromises();
    const btn = w.findAll("button").find((b) => b.text().includes("采纳 FP"));
    expect(btn).toBeTruthy();
    expect((btn!.element as HTMLButtonElement).disabled).toBe(false);
  });

  it("点采纳 FP 调 acceptDrafts 并 emit accepted", async () => {
    (aiTasksApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([
      mockTask({ status: "done", progress_pct: 100 }),
    ]);
    (functionsApi.acceptDrafts as ReturnType<typeof vi.fn>).mockResolvedValue({
      accepted: 4,
    });
    const w = mount(AiTaskPanel, { props: { open: true, projectId: "p-1" } });
    await flushPromises();
    const btn = w.findAll("button").find((b) => b.text().includes("采纳 FP"));
    await btn!.trigger("click");
    await flushPromises();
    expect(functionsApi.acceptDrafts).toHaveBeenCalledWith("p-1");
    expect(w.emitted("accepted")).toBeTruthy();
    expect(w.text()).toContain("已采纳 4 条功能点");
  });
```

- [ ] **Step 2: 跑测试确认失败** —— 命令：

```bash
cd web && npx vitest run src/__tests__/AiTaskPanel.test.ts
```

预期失败：新增 2 个用例 FAIL —— 采纳按钮 `disabled` 仍为 `true`；点击不调 `acceptDrafts`、不 emit `accepted`、无提示文案。

- [ ] **Step 3: 写最小实现** —— 在 `web/src/components/fp/AiTaskPanel.vue` 中：

3a. `<script setup>` 顶部 import 区（第 3 行 `import { formatBeijing } ...` 之后）追加：

```typescript
import { functionsApi } from "@/api/functions";
```

3b. 把 `defineEmits` 行（第 7 行）改为：

```typescript
const emit = defineEmits<{
  "update:open": [v: boolean];
  accepted: [count: number];
}>();
```

3c. 在 `onStop` 函数之后（第 56 行 `}` 之后、第 59 行 `watch(...)` 之前）追加采纳逻辑：

```typescript
const accepting = ref(false);

async function onAcceptDrafts() {
  accepting.value = true;
  hint.value = "";
  try {
    const result = await functionsApi.acceptDrafts(props.projectId);
    hint.value = `已采纳 ${result.accepted} 条功能点`;
    emit("accepted", result.accepted);
  } catch (e) {
    hint.value = e instanceof Error ? e.message : "采纳失败";
  } finally {
    accepting.value = false;
  }
}
```

3d. 模板里「采纳 FP」按钮（第 117-122 行）替换为：

```html
            <button
              v-else-if="t.status === 'done'"
              class="btn btn-sm btn-primary"
              :disabled="accepting"
              @click="onAcceptDrafts"
            >{{ accepting ? "采纳中…" : "采纳 FP" }}</button>
```

- [ ] **Step 4: 跑测试确认通过** —— 命令：

```bash
cd web && npx vitest run src/__tests__/AiTaskPanel.test.ts && npx vue-tsc --noEmit
```

预期：全部 passed（含新增 2 用例），`vue-tsc --noEmit` 0 错误。

- [ ] **Step 5: 写 FpEditor 刷新接线** —— 修改 `web/src/views/FpEditor.vue` 第 526-529 行的 `<AiTaskPanel>` 标签，加 `@accepted` 监听调用已有的 `reloadFps`：

```html
    <AiTaskPanel
      v-model:open="aiModalOpen"
      :project-id="projectId"
      @accepted="reloadFps"
    />
```

> `reloadFps`（FpEditor.vue 第 232 行）已存在 —— 它调 `load()` 重新拉 FP 列表，草稿 FP 的 `source` 变 `ai_extracted` 后黄色高亮自然消失（`fpClass` 第 228 行只对 `claude_draft` 返回 `badge-ai`）。改完跑一次校验：

```bash
cd web && npx vue-tsc --noEmit
```

预期：0 错误。

- [ ] **Step 6: 提交** —— 命令：

```bash
cd web && git add src/components/fp/AiTaskPanel.vue src/views/FpEditor.vue src/__tests__/AiTaskPanel.test.ts && git commit -m "feat(web): AiTaskPanel 采纳 FP 按钮启用 + FpEditor 联动刷新"
```

---

## Task D1: 最终全套验收

**Files:**
- 无新增 / 修改文件，仅运行验证。

- [ ] **Step 1: 后端全套 pytest** —— 命令：

```bash
cd server && .venv/bin/python -m pytest -q
```

预期：全部 passed，包含新增的 `test_v2_7_audit_global_api.py`（3）、`test_v2_7_projects_export_import_api.py`（6）、`test_v2_7_accept_drafts_api.py`（4），且既有测试（含 `test_v2_audit_log_api.py`、`test_functions_api.py`、`test_v2_project_copy.py` 等）无回归。

- [ ] **Step 2: 前端全套 vitest** —— 命令：

```bash
cd web && npx vitest run
```

预期：全部 passed，包含新增的 `AuditViewGlobal.test.ts`、`projects-export-import.test.ts`、`ProjectListSelection.test.ts`，以及改动过的 `AuditGlobalView.test.ts`、`api/functions.test.ts`、`AiTaskPanel.test.ts`，且既有测试无回归。

- [ ] **Step 3: 前端类型检查** —— 命令：

```bash
cd web && npx vue-tsc --noEmit
```

预期：0 错误。

- [ ] **Step 4: 前端生产构建** —— 命令：

```bash
cd web && npm run build
```

预期：`vue-tsc -b` + `vite build` 成功，无类型错误、无构建错误，产物写入 `web/dist/`。

- [ ] **Step 5: 提交（仅当前面步骤暴露需修复的问题时）** —— 若 Step 1-4 全绿则本 Task 无需提交。若发现回归，按 superpowers:systematic-debugging 定位根因、修复、重跑本 Task 全部步骤，再以一次 commit 收尾：

```bash
cd .. && git add -A && git commit -m "fix: v2.7 三功能补全最终验收回归修复"
```

---

## 验收对照（spec → 计划映射）

- 功能 1 全局审计：Task A1（service）+ A2（端点 + schema）+ A3（client + 徽章）+ A4（view）→ 覆盖 spec「后端 GET /api/audit + list_global + project_name」「前端 listGlobal + 时间线 + 项目徽章 + 加载更多」「多项目混合倒序 / keyset / 空库」测试。
- 功能 2 导出导入：Task B1（schema + service）+ B2（端点）+ B3（client）+ B4（UI）→ 覆盖 spec「export/import bundle 结构、跳过不存在 id、非法 bundle 400、新建项目、复选框 + 全选、Blob 下载、文件导入、卡片视图提示」。
- 功能 3 采纳 FP：Task C1（service + 端点）+ C2（client）+ C3（按钮 + 联动）→ 覆盖 spec「accept-drafts 快照 + claude_draft→ai_extracted、无草稿 accepted=0、404、按钮启用、刷新提示、高亮自然消失」。
- 全局验收：Task D1 跑全套 pytest / vitest / vue-tsc / build。无 alembic migration（三功能均无 schema 变更）。
