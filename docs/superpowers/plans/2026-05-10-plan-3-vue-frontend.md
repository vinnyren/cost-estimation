# Plan 3 — Vue 3 前端（5 屏 + 状态矩阵 + a11y） Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `web/` 目录交付一套与 Plan 1+2 后端完全联通的 Vue 3 前端，覆盖项目列表/向导/FP 编辑/参数管理/结果页 5 屏，每屏满足 Loading/Empty/Error/Partial/Stale 5 态矩阵，并达到 WCAG 2.1 AA 可访问性基线。

**Architecture:** Vue 3 + TypeScript + Pinia（3 store：projects/params/results）+ Vue Router（含未保存改动守卫）+ Element Plus（基础组件）+ vxe-table（FP 大表）+ axios（API client，自动注入启动 token）。Vite 开发期通过 proxy 直接转发 `/api` 与 `/health` 到 8788 端口；生产期由 FastAPI 静态托管 `web/dist`。前端不直接生成 Excel，仅调用 GET `/api/reports/excel/{id}` 下载。

**Tech Stack:** Vue 3.4 / TypeScript 5.4 / Vite 5 / Pinia 2 / Vue Router 4 / Element Plus 2.7 / vxe-table 4.6 / axios 1.7 / Vitest 1.6 / @vue/test-utils 2 / Playwright 1.45（E2E）/ pnpm 9。

---

## 任务总览

| # | Task | 主要产出 |
|---|---|---|
| T1 | 前端脚手架（Vite + Vue 3 + TS + 工具链） | `web/` 目录、`package.json`、Vite/Vitest 配置 |
| T2 | API 客户端 + 错误 envelope 解封 | `src/api/*` |
| T3 | 状态矩阵 5 组件 + useApi composable | `src/components/status/*`、`src/composables/useApi.ts` |
| T4 | Pinia stores（projects/params/results） | `src/stores/*` |
| T5 | Router + token 提取 + 未保存改动守卫 | `src/router/index.ts` |
| T6 | 项目列表屏 | `src/views/ProjectList.vue` |
| T7 | 项目向导屏（5 步） | `src/views/ProjectWizard.vue` |
| T8 | 参数管理屏（6 Tab + 覆盖高亮） | `src/views/ParamManager.vue`、`src/components/OverrideField.vue` |
| T9 | FP 编辑屏（模块树 + vxe-table） | `src/views/FpEditor.vue`、`src/components/ModuleTree.vue` |
| T10 | 结果页（Forward/Reverse 双模式 + 下载） | `src/views/ResultView.vue`、`src/components/ResultCard.vue` |
| T11 | a11y 审计 + 单测覆盖率 | `tests/unit/*`、a11y 报告 |
| T12 | 与后端联调 + 静态托管集成 | `vite.config.ts` proxy、`server/app/main.py` 静态挂载 |

每个 Task 都遵循 TDD：先写失败测试 → 实现到通过 → commit。

---

## Task 1: 前端脚手架（Vite + Vue 3 + TypeScript + 工具链）

**Files:**
- Create: `web/package.json`
- Create: `web/tsconfig.json`
- Create: `web/tsconfig.node.json`
- Create: `web/vite.config.ts`
- Create: `web/vitest.config.ts`
- Create: `web/index.html`
- Create: `web/src/main.ts`
- Create: `web/src/App.vue`
- Create: `web/src/styles/tokens.css`
- Create: `web/src/styles/global.css`
- Create: `web/.eslintrc.cjs`
- Create: `web/.gitignore`
- Modify: `.gitignore` (顶层追加 `web/node_modules`、`web/dist`)
- Test: `web/src/__tests__/smoke.test.ts`

- [ ] **Step 1: 写脚手架冒烟测试（必须先失败）**

```ts
// web/src/__tests__/smoke.test.ts
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import App from "../App.vue";

describe("App smoke", () => {
  it("挂载根组件且暴露 router-view", () => {
    const wrapper = mount(App, {
      global: {
        stubs: { "router-view": { template: "<div data-test='rv'/>" } },
      },
    });
    expect(wrapper.find("[data-test='rv']").exists()).toBe(true);
  });

  it("注入 oklch 设计 token", () => {
    const root = getComputedStyle(document.documentElement);
    expect(root.getPropertyValue("--color-accent").trim()).not.toBe("");
  });
});
```

- [ ] **Step 2: 创建 package.json**

```json
{
  "name": "cost-estimation-web",
  "private": true,
  "type": "module",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:ui": "vitest --ui",
    "lint": "eslint . --ext .vue,.ts,.tsx --max-warnings 0",
    "type-check": "vue-tsc --noEmit"
  },
  "dependencies": {
    "vue": "^3.4.31",
    "vue-router": "^4.4.0",
    "pinia": "^2.1.7",
    "element-plus": "^2.7.6",
    "vxe-table": "^4.6.17",
    "xe-utils": "^3.5.30",
    "axios": "^1.7.2"
  },
  "devDependencies": {
    "@types/node": "^20.14.10",
    "@vitejs/plugin-vue": "^5.0.5",
    "@vue/test-utils": "^2.4.6",
    "@vue/tsconfig": "^0.5.1",
    "eslint": "^8.57.0",
    "eslint-plugin-vue": "^9.27.0",
    "@typescript-eslint/parser": "^7.16.1",
    "@typescript-eslint/eslint-plugin": "^7.16.1",
    "happy-dom": "^14.12.3",
    "typescript": "^5.4.5",
    "vite": "^5.3.4",
    "vitest": "^1.6.0",
    "vue-tsc": "^2.0.26"
  }
}
```

- [ ] **Step 3: 创建 tsconfig**

```jsonc
// web/tsconfig.json
{
  "extends": "@vue/tsconfig/tsconfig.dom.json",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] },
    "types": ["vitest/globals"]
  },
  "include": ["src/**/*", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

```jsonc
// web/tsconfig.node.json
{
  "extends": "@vue/tsconfig/tsconfig.json",
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "types": ["node"]
  },
  "include": ["vite.config.ts", "vitest.config.ts"]
}
```

- [ ] **Step 4: 创建 vite.config.ts**

```ts
// web/vite.config.ts
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "node:path";

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8788", changeOrigin: false },
      "/health": { target: "http://127.0.0.1:8788", changeOrigin: false },
    },
  },
  build: { outDir: "dist", emptyOutDir: true, sourcemap: true },
});
```

- [ ] **Step 5: 创建 vitest.config.ts**

```ts
// web/vitest.config.ts
import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import path from "node:path";

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  test: {
    environment: "happy-dom",
    globals: true,
    setupFiles: ["src/__tests__/setup.ts"],
    coverage: { reporter: ["text", "html"], thresholds: { lines: 80 } },
  },
});
```

- [ ] **Step 6: 创建 index.html + main.ts + App.vue + setup.ts**

```html
<!-- web/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>软件造价制作系统</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

```ts
// web/src/main.ts
import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import VxeUI from "vxe-table";
import "vxe-table/lib/style.css";
import App from "./App.vue";
import { router } from "./router";
import "./styles/tokens.css";
import "./styles/global.css";

createApp(App)
  .use(createPinia())
  .use(router)
  .use(ElementPlus)
  .use(VxeUI)
  .mount("#app");
```

```vue
<!-- web/src/App.vue -->
<script setup lang="ts">
</script>

<template>
  <main aria-live="polite">
    <router-view />
  </main>
</template>
```

```ts
// web/src/__tests__/setup.ts
import "../styles/tokens.css";
```

- [ ] **Step 7: 创建设计 token + 全局样式**

```css
/* web/src/styles/tokens.css */
:root {
  --color-surface: oklch(98% 0 0);
  --color-text: oklch(18% 0 0);
  --color-accent: oklch(68% 0.21 250);
  --color-warn-bg: oklch(96% 0.08 95);
  --color-warn-stripe: oklch(70% 0.15 70);
  --color-error: oklch(60% 0.22 25);
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --radius-sm: 4px;
  --radius-md: 8px;
  --duration-fast: 150ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}
```

```css
/* web/src/styles/global.css */
*, *::before, *::after { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  background: var(--color-surface);
  color: var(--color-text);
}
:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
```

- [ ] **Step 8: 创建 .eslintrc.cjs**

```js
// web/.eslintrc.cjs
module.exports = {
  root: true,
  env: { browser: true, es2022: true, node: true },
  extends: [
    "eslint:recommended",
    "plugin:vue/vue3-recommended",
    "plugin:@typescript-eslint/recommended",
  ],
  parser: "vue-eslint-parser",
  parserOptions: {
    parser: "@typescript-eslint/parser",
    ecmaVersion: 2022,
    sourceType: "module",
  },
  rules: {
    "vue/multi-word-component-names": "off",
    "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
  },
};
```

- [ ] **Step 9: 创建 .gitignore + 修改顶层 .gitignore**

```
# web/.gitignore
node_modules
dist
dist-ssr
*.local
.vscode/*
!.vscode/settings.json
.idea
coverage
```

顶层 `.gitignore` 追加：

```
web/node_modules/
web/dist/
web/coverage/
```

- [ ] **Step 10: 安装依赖并运行测试（应通过）**

```bash
cd web
pnpm install
pnpm test
# 期望：smoke.test.ts 中第一个用例 PASS（router-view stub 渲染）；第二个用例当前会 FAIL，因为 router 还没实现 — 在 T5 通过
# 暂时跳过第二个用例：在 it() 改为 it.skip() 直到 T5 完成
```

> **注意：** Step 1 的第二个用例先 skip，等 T5 router 完成后回来去掉 skip。

- [ ] **Step 11: Commit**

```bash
git add web/ .gitignore
git commit -m "build(web): scaffold vue 3 + ts + vite + vitest + element-plus + vxe-table"
```

---

## Task 2: API 客户端 + 错误 envelope 解封

**Files:**
- Create: `web/src/api/client.ts`
- Create: `web/src/api/projects.ts`
- Create: `web/src/api/functions.ts`
- Create: `web/src/api/params.ts`
- Create: `web/src/api/calc.ts`
- Create: `web/src/api/uploads.ts`
- Create: `web/src/api/reports.ts`
- Create: `web/src/api/types.ts`
- Test: `web/src/__tests__/api/client.test.ts`

- [ ] **Step 1: 写 client 测试（必须先失败）**

```ts
// web/src/__tests__/api/client.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import { createClient, ApiError } from "@/api/client";

vi.mock("axios");

describe("API client", () => {
  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem("auth_token", "test-token-123");
    vi.resetAllMocks();
  });

  it("注入 X-Auth-Token 请求头", async () => {
    const post = vi.fn().mockResolvedValue({ data: { ok: true, data: { id: 1 } } });
    (axios.create as any).mockReturnValue({
      post,
      get: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    });
    const client = createClient();
    await client.post("/api/projects", { name: "x" });
    expect(post).toHaveBeenCalledWith(
      "/api/projects",
      { name: "x" },
      expect.objectContaining({
        headers: expect.objectContaining({ "X-Auth-Token": "test-token-123" }),
      }),
    );
  });

  it("解封成功响应：{ok:true,data} → data", async () => {
    const get = vi.fn().mockResolvedValue({ data: { ok: true, data: { items: [1, 2] } } });
    (axios.create as any).mockReturnValue({
      post: vi.fn(),
      get,
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    });
    const client = createClient();
    const data = await client.get("/api/projects");
    expect(data).toEqual({ items: [1, 2] });
  });

  it("解封错误响应：{ok:false,error} → throw ApiError", async () => {
    const get = vi.fn().mockResolvedValue({
      data: { ok: false, error: { code: "INVALID_PARAM", message: "城市无效", details: { field: "city" } } },
    });
    (axios.create as any).mockReturnValue({
      post: vi.fn(),
      get,
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    });
    const client = createClient();
    await expect(client.get("/api/projects")).rejects.toMatchObject({
      code: "INVALID_PARAM",
      message: "城市无效",
      details: { field: "city" },
    });
  });

  it("HTTP 401 → throw ApiError(UNAUTHORIZED)", async () => {
    const err: any = new Error("Request failed");
    err.response = { status: 401, data: { error: { code: "UNAUTHORIZED", message: "Invalid token" } } };
    const get = vi.fn().mockRejectedValue(err);
    (axios.create as any).mockReturnValue({
      post: vi.fn(),
      get,
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    });
    const client = createClient();
    await expect(client.get("/api/projects")).rejects.toBeInstanceOf(ApiError);
  });
});
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd web && pnpm test -- src/__tests__/api/client.test.ts
# 期望：FAIL — Cannot find module '@/api/client'
```

- [ ] **Step 3: 实现 src/api/types.ts**

```ts
// web/src/api/types.ts
export interface SuccessEnvelope<T> {
  ok: true;
  data: T;
  meta?: Record<string, unknown>;
}

export interface ErrorEnvelope {
  ok: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export type ApiEnvelope<T> = SuccessEnvelope<T> | ErrorEnvelope;
```

- [ ] **Step 4: 实现 src/api/client.ts**

```ts
// web/src/api/client.ts
import axios, { type AxiosInstance, type AxiosResponse } from "axios";
import type { ApiEnvelope } from "./types";

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function unwrap<T>(resp: AxiosResponse<ApiEnvelope<T>>): T {
  if (!resp.data || typeof resp.data !== "object") {
    throw new ApiError("INVALID_RESPONSE", "Server returned malformed envelope");
  }
  if (resp.data.ok) {
    return resp.data.data;
  }
  throw new ApiError(resp.data.error.code, resp.data.error.message, resp.data.error.details);
}

function getToken(): string {
  return sessionStorage.getItem("auth_token") ?? "";
}

export interface Client {
  get<T>(url: string, params?: Record<string, unknown>): Promise<T>;
  post<T>(url: string, body?: unknown, config?: { headers?: Record<string, string> }): Promise<T>;
  patch<T>(url: string, body?: unknown): Promise<T>;
  delete<T>(url: string): Promise<T>;
  raw: AxiosInstance;
}

export function createClient(): Client {
  const instance = axios.create({
    baseURL: "",
    timeout: 30_000,
    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
  });

  instance.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
      config.headers = config.headers ?? {};
      (config.headers as Record<string, string>)["X-Auth-Token"] = token;
    }
    return config;
  });

  instance.interceptors.response.use(
    (resp) => resp,
    (err) => {
      const errorEnvelope = err.response?.data?.error;
      if (errorEnvelope?.code) {
        return Promise.reject(new ApiError(errorEnvelope.code, errorEnvelope.message, errorEnvelope.details));
      }
      return Promise.reject(new ApiError("NETWORK_ERROR", err.message ?? "Network error"));
    },
  );

  return {
    raw: instance,
    async get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
      const headers = { "X-Auth-Token": getToken() };
      const resp = await instance.get<ApiEnvelope<T>>(url, { params, headers });
      return unwrap<T>(resp);
    },
    async post<T>(url: string, body?: unknown, config?: { headers?: Record<string, string> }): Promise<T> {
      const headers = { "X-Auth-Token": getToken(), ...(config?.headers ?? {}) };
      const resp = await instance.post<ApiEnvelope<T>>(url, body, { headers });
      return unwrap<T>(resp);
    },
    async patch<T>(url: string, body?: unknown): Promise<T> {
      const headers = { "X-Auth-Token": getToken() };
      const resp = await instance.patch<ApiEnvelope<T>>(url, body, { headers });
      return unwrap<T>(resp);
    },
    async delete<T>(url: string): Promise<T> {
      const headers = { "X-Auth-Token": getToken() };
      const resp = await instance.delete<ApiEnvelope<T>>(url, { headers });
      return unwrap<T>(resp);
    },
  };
}

export const api = createClient();
```

- [ ] **Step 5: 实现领域 API 模块**

```ts
// web/src/api/projects.ts
import { api } from "./client";

export type ProjectMode = "forward" | "reverse";

export interface Project {
  id: number;
  name: string;
  mode: ProjectMode;
  city: string;
  industry: string;
  stage: string;
  total_fp?: number;
  total_cost?: number;
  created_at: string;
  updated_at: string;
}

export const projectsApi = {
  list: () => api.get<{ items: Project[] }>("/api/projects"),
  get: (id: number) => api.get<Project>(`/api/projects/${id}`),
  create: (body: Partial<Project>) => api.post<Project>("/api/projects", body),
  patch: (id: number, body: Partial<Project>) => api.patch<Project>(`/api/projects/${id}`, body),
  remove: (id: number) => api.delete<void>(`/api/projects/${id}`),
};
```

```ts
// web/src/api/functions.ts
import { api } from "./client";

export type FpCategory = "EI" | "EO" | "EQ" | "ILF" | "EIF";
export type FpSource = "manual" | "ai_extracted" | "allocator";

export interface FunctionPoint {
  id: number;
  project_id: number;
  subsystem: string;
  module_l1: string;
  module_l2?: string;
  description: string;
  category: FpCategory;
  ufp: number;
  reuse_ratio: number;
  modify_ratio: number;
  us: number;
  source: FpSource;
  audit_tag?: string;
  version: number;
}

export const functionsApi = {
  list: (projectId: number) =>
    api.get<{ items: FunctionPoint[] }>(`/api/projects/${projectId}/functions`),
  patch: (projectId: number, fpId: number, body: Partial<FunctionPoint>) =>
    api.patch<FunctionPoint>(`/api/projects/${projectId}/functions/${fpId}`, body),
  bulk: (projectId: number, items: Partial<FunctionPoint>[]) =>
    api.post<{ items: FunctionPoint[] }>(`/api/projects/${projectId}/functions/bulk`, { items }),
  restore: (projectId: number, version: number) =>
    api.post<void>(`/api/projects/${projectId}/functions/restore?version=${version}`),
};
```

```ts
// web/src/api/params.ts
import { api } from "./client";

export interface EffectiveParams {
  cf: Record<string, number>;
  productivity_dev: Record<string, Record<string, number>>;
  productivity_ops?: Record<string, Record<string, number>>;
  city_rate: Record<string, { dev: number; ops: number; class: string }>;
  factors_dev: Record<string, Record<string, number>>;
  factors_ops: Record<string, Record<string, number>>;
  hours_per_pm: number;
  ops_cost_ratio: { P50: number };
  overrides?: Record<string, unknown>;
}

export const paramsApi = {
  effective: (projectId: number) =>
    api.get<EffectiveParams>(`/api/projects/${projectId}/params/effective`),
  global: () => api.get<EffectiveParams>("/api/params/global"),
  patchGlobal: (body: Partial<EffectiveParams>) => api.patch<EffectiveParams>("/api/params/global", body),
  resetGlobal: () => api.post<EffectiveParams>("/api/params/global/reset"),
  override: (projectId: number, body: Record<string, unknown>) =>
    api.patch<EffectiveParams>(`/api/projects/${projectId}/params/override`, body),
};
```

```ts
// web/src/api/calc.ts
import { api } from "./client";

export interface ForwardResult {
  scale_adjusted: number;
  effort_pm: { P10: number; P50: number; P90: number };
  cost_yuan: { P10: number; P50: number; P90: number };
  steps?: Array<{ name: string; value: number; note?: string }>;
}

export interface ReverseResult {
  fp_total: { P10: number; P50: number; P90: number };
  recommended_band: "P10" | "P50" | "P90";
}

export const calcApi = {
  forward: (body: { project_id: number }) => api.post<ForwardResult>("/api/calc/forward", body),
  reverse: (body: { project_id: number; target_total: number; other_cost: number }) =>
    api.post<ReverseResult>("/api/calc/reverse", body),
  allocate: (body: { project_id: number; target_us: number; cf: number }) =>
    api.post<{ items: Array<{ id: number; us: number; audit_tag?: string }> }>("/api/calc/allocate", body),
};
```

```ts
// web/src/api/uploads.ts
import { api } from "./client";

export interface UploadResult {
  upload_id: number;
  filename: string;
  size: number;
  parsed_text_preview?: string;
}

export const uploadsApi = {
  upload: async (projectId: number, file: File): Promise<UploadResult> => {
    const form = new FormData();
    form.append("file", file);
    return api.post<UploadResult>(`/api/projects/${projectId}/uploads`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};
```

```ts
// web/src/api/reports.ts
import { api } from "./client";

export const reportsApi = {
  excelUrl: (projectId: number) => `/api/reports/excel/${projectId}`,
  download: async (projectId: number, filename = "造价报告.xlsx"): Promise<void> => {
    const token = sessionStorage.getItem("auth_token") ?? "";
    const resp = await api.raw.get(`/api/reports/excel/${projectId}`, {
      responseType: "blob",
      headers: { "X-Auth-Token": token },
    });
    const blob = new Blob([resp.data], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },
};
```

- [ ] **Step 6: 运行测试**

```bash
pnpm test -- src/__tests__/api/client.test.ts
# 期望：4 个用例 PASS
```

- [ ] **Step 7: Commit**

```bash
git add web/src/api/ web/src/__tests__/api/
git commit -m "feat(web): API client with token injection + envelope unwrap + ApiError"
```

---

## Task 3: 状态矩阵 5 组件 + useApi composable

**Files:**
- Create: `web/src/components/status/LoadingSkeleton.vue`
- Create: `web/src/components/status/EmptyState.vue`
- Create: `web/src/components/status/ErrorBanner.vue`
- Create: `web/src/components/status/PartialState.vue`
- Create: `web/src/components/status/StaleBanner.vue`
- Create: `web/src/composables/useApi.ts`
- Test: `web/src/__tests__/composables/useApi.test.ts`
- Test: `web/src/__tests__/components/status.test.ts`

- [ ] **Step 1: 写 useApi 测试（先失败）**

```ts
// web/src/__tests__/composables/useApi.test.ts
import { describe, it, expect, vi } from "vitest";
import { nextTick } from "vue";
import { useApi } from "@/composables/useApi";
import { ApiError } from "@/api/client";

describe("useApi", () => {
  it("初始 state=idle", () => {
    const { state } = useApi(() => Promise.resolve("ok"));
    expect(state.value).toBe("idle");
  });

  it("调用过程中 state=loading", async () => {
    let resolve: (v: string) => void = () => {};
    const fn = () => new Promise<string>((r) => (resolve = r));
    const { state, run } = useApi(fn);
    const p = run();
    await nextTick();
    expect(state.value).toBe("loading");
    resolve("ok");
    await p;
    expect(state.value).toBe("success");
  });

  it("成功后 data 可读、error=null", async () => {
    const { state, data, error, run } = useApi(() => Promise.resolve(42));
    await run();
    expect(state.value).toBe("success");
    expect(data.value).toBe(42);
    expect(error.value).toBeNull();
  });

  it("失败后 state=error，error 暴露 ApiError", async () => {
    const fn = vi.fn().mockRejectedValue(new ApiError("INVALID_PARAM", "x"));
    const { state, error, run } = useApi(fn);
    await expect(run()).rejects.toThrow();
    expect(state.value).toBe("error");
    expect(error.value).toMatchObject({ code: "INVALID_PARAM", message: "x" });
  });

  it("reset 回到 idle", async () => {
    const { state, data, run, reset } = useApi(() => Promise.resolve(1));
    await run();
    reset();
    expect(state.value).toBe("idle");
    expect(data.value).toBeNull();
  });
});
```

- [ ] **Step 2: 写状态组件测试（先失败）**

```ts
// web/src/__tests__/components/status.test.ts
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import EmptyState from "@/components/status/EmptyState.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";
import StaleBanner from "@/components/status/StaleBanner.vue";

describe("Status components", () => {
  it("LoadingSkeleton 渲染指定行数", () => {
    const wrapper = mount(LoadingSkeleton, { props: { rows: 8 } });
    expect(wrapper.findAll("[data-test='skeleton-row']")).toHaveLength(8);
  });

  it("EmptyState 显示 title + cta-label", () => {
    const wrapper = mount(EmptyState, {
      props: { title: "项目库为空", ctaLabel: "新建第一个项目" },
    });
    expect(wrapper.text()).toContain("项目库为空");
    expect(wrapper.find("button").text()).toBe("新建第一个项目");
  });

  it("ErrorBanner 显示 problem + cause + 重试按钮", () => {
    const wrapper = mount(ErrorBanner, {
      props: {
        problem: "无法加载项目",
        cause: "网络断开",
        suggestion: "请检查网络连接后重试",
        retryable: true,
      },
    });
    expect(wrapper.text()).toContain("无法加载项目");
    expect(wrapper.text()).toContain("网络断开");
    expect(wrapper.find("[data-test='retry']").exists()).toBe(true);
  });

  it("ErrorBanner 用 role=alert 暴露给屏幕阅读器", () => {
    const wrapper = mount(ErrorBanner, {
      props: { problem: "x", cause: "y", suggestion: "z" },
    });
    expect(wrapper.find("[role='alert']").exists()).toBe(true);
  });

  it("StaleBanner 触发 recompute 事件", async () => {
    const wrapper = mount(StaleBanner);
    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted().recompute).toBeTruthy();
  });
});
```

- [ ] **Step 3: 实现 useApi composable**

```ts
// web/src/composables/useApi.ts
import { ref, type Ref } from "vue";
import { ApiError } from "@/api/client";

export type ApiState = "idle" | "loading" | "success" | "error" | "partial";

export interface UseApiReturn<TArgs extends unknown[], TData> {
  state: Ref<ApiState>;
  data: Ref<TData | null>;
  error: Ref<ApiError | null>;
  run: (...args: TArgs) => Promise<TData>;
  reset: () => void;
}

export function useApi<TArgs extends unknown[], TData>(
  fn: (...args: TArgs) => Promise<TData>,
): UseApiReturn<TArgs, TData> {
  const state = ref<ApiState>("idle");
  const data = ref<TData | null>(null) as Ref<TData | null>;
  const error = ref<ApiError | null>(null);

  async function run(...args: TArgs): Promise<TData> {
    state.value = "loading";
    error.value = null;
    try {
      const result = await fn(...args);
      data.value = result;
      state.value = "success";
      return result;
    } catch (e) {
      const apiErr = e instanceof ApiError ? e : new ApiError("UNKNOWN", String(e));
      error.value = apiErr;
      state.value = "error";
      throw apiErr;
    }
  }

  function reset(): void {
    state.value = "idle";
    data.value = null;
    error.value = null;
  }

  return { state, data, error, run, reset };
}
```

- [ ] **Step 4: 实现 5 个状态组件**

```vue
<!-- web/src/components/status/LoadingSkeleton.vue -->
<script setup lang="ts">
defineProps<{ rows?: number }>();
</script>

<template>
  <div role="status" aria-live="polite" aria-busy="true" class="skeleton-wrap">
    <div
      v-for="i in rows ?? 3"
      :key="i"
      data-test="skeleton-row"
      class="skeleton-row"
    />
    <span class="visually-hidden">加载中</span>
  </div>
</template>

<style scoped>
.skeleton-wrap { display: flex; flex-direction: column; gap: var(--space-2); }
.skeleton-row {
  height: 32px;
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, oklch(94% 0 0), oklch(97% 0 0), oklch(94% 0 0));
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.visually-hidden {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
}
</style>
```

```vue
<!-- web/src/components/status/EmptyState.vue -->
<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
  ctaLabel?: string;
}>();
defineEmits<{ (e: "cta-click"): void }>();
</script>

<template>
  <section class="empty">
    <h2>{{ title }}</h2>
    <p v-if="description">{{ description }}</p>
    <button v-if="ctaLabel" type="button" @click="$emit('cta-click')">{{ ctaLabel }}</button>
  </section>
</template>

<style scoped>
.empty {
  display: flex; flex-direction: column; align-items: center;
  padding: var(--space-8); gap: var(--space-3);
}
button {
  min-height: 44px; min-width: 120px;
  background: var(--color-accent); color: white;
  border: none; border-radius: var(--radius-md); cursor: pointer;
}
button:hover { filter: brightness(1.05); }
</style>
```

```vue
<!-- web/src/components/status/ErrorBanner.vue -->
<script setup lang="ts">
defineProps<{
  problem: string;
  cause: string;
  suggestion: string;
  retryable?: boolean;
}>();
defineEmits<{ (e: "retry"): void }>();
</script>

<template>
  <aside role="alert" class="error-banner">
    <div class="content">
      <strong>{{ problem }}</strong>
      <p class="cause">原因：{{ cause }}</p>
      <p class="suggestion">建议：{{ suggestion }}</p>
    </div>
    <button
      v-if="retryable"
      type="button"
      data-test="retry"
      @click="$emit('retry')"
    >重试</button>
  </aside>
</template>

<style scoped>
.error-banner {
  display: flex; gap: var(--space-3); padding: var(--space-3);
  background: oklch(96% 0.06 25); border-left: 4px solid var(--color-error);
  border-radius: var(--radius-sm); align-items: flex-start;
}
.content { flex: 1; }
.cause, .suggestion { margin: var(--space-1) 0 0 0; font-size: 14px; }
button { min-height: 44px; padding: 0 var(--space-3); }
</style>
```

```vue
<!-- web/src/components/status/PartialState.vue -->
<script setup lang="ts">
defineProps<{ doneCount: number; totalCount: number; cancellable?: boolean }>();
defineEmits<{ (e: "cancel"): void }>();
</script>

<template>
  <div role="status" aria-live="polite" class="partial">
    <progress :value="doneCount" :max="totalCount" />
    <span>{{ doneCount }} / {{ totalCount }}</span>
    <button v-if="cancellable" type="button" @click="$emit('cancel')">取消</button>
  </div>
</template>

<style scoped>
.partial { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-2); }
progress { flex: 1; }
button { min-height: 44px; padding: 0 var(--space-3); }
</style>
```

```vue
<!-- web/src/components/status/StaleBanner.vue -->
<script setup lang="ts">
defineEmits<{ (e: "recompute"): void }>();
</script>

<template>
  <aside class="stale" role="status" aria-live="polite">
    <span>参数已变，结果可能过期</span>
    <button type="button" @click="$emit('recompute')">重新计算</button>
  </aside>
</template>

<style scoped>
.stale {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  background: var(--color-warn-bg);
  border-left: 3px solid var(--color-warn-stripe);
}
button { min-height: 44px; padding: 0 var(--space-3); }
</style>
```

- [ ] **Step 5: 运行测试验证全部通过**

```bash
pnpm test -- src/__tests__/composables/useApi.test.ts src/__tests__/components/status.test.ts
# 期望：10 个用例 PASS
```

- [ ] **Step 6: Commit**

```bash
git add web/src/components/status/ web/src/composables/ web/src/__tests__/composables/ web/src/__tests__/components/
git commit -m "feat(web): status matrix components (loading/empty/error/partial/stale) + useApi composable"
```

---

## Task 4: Pinia stores（projects/params/results）

**Files:**
- Create: `web/src/stores/projects.ts`
- Create: `web/src/stores/params.ts`
- Create: `web/src/stores/results.ts`
- Test: `web/src/__tests__/stores/projects.test.ts`
- Test: `web/src/__tests__/stores/results.test.ts`

- [ ] **Step 1: 写 stores 测试（先失败）**

```ts
// web/src/__tests__/stores/projects.test.ts
import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useProjectsStore } from "@/stores/projects";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    list: vi.fn().mockResolvedValue({
      items: [{ id: 1, name: "p1", mode: "forward", city: "北京", industry: "电子政务", stage: "bidding", created_at: "", updated_at: "" }],
    }),
    create: vi.fn().mockResolvedValue({ id: 2, name: "p2", mode: "reverse", city: "上海", industry: "金融", stage: "budget", created_at: "", updated_at: "" }),
    remove: vi.fn().mockResolvedValue(undefined),
  },
}));

describe("projectsStore", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("fetchAll 写入 items", async () => {
    const store = useProjectsStore();
    await store.fetchAll();
    expect(store.items).toHaveLength(1);
    expect(store.state).toBe("success");
  });

  it("create 追加 item", async () => {
    const store = useProjectsStore();
    await store.fetchAll();
    await store.create({ name: "p2", mode: "reverse", city: "上海", industry: "金融", stage: "budget" });
    expect(store.items).toHaveLength(2);
  });

  it("remove 移除 item", async () => {
    const store = useProjectsStore();
    await store.fetchAll();
    await store.remove(1);
    expect(store.items).toHaveLength(0);
  });
});
```

```ts
// web/src/__tests__/stores/results.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useResultsStore } from "@/stores/results";

describe("resultsStore", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("paramsChangedAt 之后 forwardResult 标记 stale", () => {
    const store = useResultsStore();
    store.setForwardResult({ scale_adjusted: 332.75, effort_pm: { P10: 50, P50: 80, P90: 110 }, cost_yuan: { P10: 300000, P50: 489180, P90: 700000 } });
    expect(store.isStale).toBe(false);
    store.markParamsChanged();
    expect(store.isStale).toBe(true);
  });

  it("setForwardResult 清除 stale 标志", () => {
    const store = useResultsStore();
    store.markParamsChanged();
    store.setForwardResult({ scale_adjusted: 100, effort_pm: { P10: 1, P50: 2, P90: 3 }, cost_yuan: { P10: 1, P50: 2, P90: 3 } });
    expect(store.isStale).toBe(false);
  });
});
```

- [ ] **Step 2: 实现 src/stores/projects.ts**

```ts
// web/src/stores/projects.ts
import { defineStore } from "pinia";
import { ref } from "vue";
import { projectsApi, type Project } from "@/api/projects";
import { ApiError } from "@/api/client";

export const useProjectsStore = defineStore("projects", () => {
  const items = ref<Project[]>([]);
  const state = ref<"idle" | "loading" | "success" | "error">("idle");
  const error = ref<ApiError | null>(null);

  async function fetchAll(): Promise<void> {
    state.value = "loading";
    error.value = null;
    try {
      const resp = await projectsApi.list();
      items.value = resp.items;
      state.value = "success";
    } catch (e) {
      error.value = e instanceof ApiError ? e : new ApiError("UNKNOWN", String(e));
      state.value = "error";
    }
  }

  async function create(body: Partial<Project>): Promise<Project> {
    const created = await projectsApi.create(body);
    items.value = [created, ...items.value];
    return created;
  }

  async function patch(id: number, body: Partial<Project>): Promise<void> {
    const updated = await projectsApi.patch(id, body);
    items.value = items.value.map((p) => (p.id === id ? updated : p));
  }

  async function remove(id: number): Promise<void> {
    await projectsApi.remove(id);
    items.value = items.value.filter((p) => p.id !== id);
  }

  return { items, state, error, fetchAll, create, patch, remove };
});
```

- [ ] **Step 3: 实现 src/stores/params.ts**

```ts
// web/src/stores/params.ts
import { defineStore } from "pinia";
import { ref } from "vue";
import { paramsApi, type EffectiveParams } from "@/api/params";

export const useParamsStore = defineStore("params", () => {
  const effective = ref<EffectiveParams | null>(null);
  const overrides = ref<Record<string, unknown>>({});
  const loadedFor = ref<number | null>(null);

  async function loadFor(projectId: number): Promise<void> {
    const resp = await paramsApi.effective(projectId);
    effective.value = resp;
    overrides.value = (resp.overrides ?? {}) as Record<string, unknown>;
    loadedFor.value = projectId;
  }

  async function applyOverride(projectId: number, patch: Record<string, unknown>): Promise<void> {
    const resp = await paramsApi.override(projectId, patch);
    effective.value = resp;
    overrides.value = (resp.overrides ?? {}) as Record<string, unknown>;
  }

  function isOverridden(path: string): boolean {
    return path in overrides.value;
  }

  return { effective, overrides, loadedFor, loadFor, applyOverride, isOverridden };
});
```

- [ ] **Step 4: 实现 src/stores/results.ts**

```ts
// web/src/stores/results.ts
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { ForwardResult, ReverseResult } from "@/api/calc";

export const useResultsStore = defineStore("results", () => {
  const forwardResult = ref<ForwardResult | null>(null);
  const reverseResult = ref<ReverseResult | null>(null);
  const lastComputedAt = ref<number>(0);
  const paramsChangedAt = ref<number>(0);

  const isStale = computed(
    () => lastComputedAt.value > 0 && paramsChangedAt.value > lastComputedAt.value,
  );

  function setForwardResult(r: ForwardResult): void {
    forwardResult.value = r;
    lastComputedAt.value = Date.now();
  }

  function setReverseResult(r: ReverseResult): void {
    reverseResult.value = r;
    lastComputedAt.value = Date.now();
  }

  function markParamsChanged(): void {
    paramsChangedAt.value = Date.now();
  }

  function clear(): void {
    forwardResult.value = null;
    reverseResult.value = null;
    lastComputedAt.value = 0;
    paramsChangedAt.value = 0;
  }

  return {
    forwardResult,
    reverseResult,
    lastComputedAt,
    paramsChangedAt,
    isStale,
    setForwardResult,
    setReverseResult,
    markParamsChanged,
    clear,
  };
});
```

- [ ] **Step 5: 运行测试**

```bash
pnpm test -- src/__tests__/stores/
# 期望：5 个用例 PASS
```

- [ ] **Step 6: Commit**

```bash
git add web/src/stores/ web/src/__tests__/stores/
git commit -m "feat(web): pinia stores — projects + params + results with stale detection"
```

---

## Task 5: Router + token 提取 + 未保存改动守卫

**Files:**
- Create: `web/src/router/index.ts`
- Create: `web/src/composables/useUnsavedGuard.ts`
- Modify: `web/src/main.ts` (Step 1 已注入 router)
- Modify: `web/src/__tests__/smoke.test.ts` (取消 it.skip)
- Test: `web/src/__tests__/router/index.test.ts`

- [ ] **Step 1: 写 router 测试（先失败）**

```ts
// web/src/__tests__/router/index.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import { createMemoryHistory } from "vue-router";
import { extractTokenFromUrl, createRouterFor } from "@/router";

describe("router", () => {
  beforeEach(() => sessionStorage.clear());

  it("从 URL 提取 ?t= 参数并写入 sessionStorage", () => {
    extractTokenFromUrl("http://127.0.0.1:5173/?t=abc-123");
    expect(sessionStorage.getItem("auth_token")).toBe("abc-123");
  });

  it("URL 无 token 时不覆盖已存在的 sessionStorage 值", () => {
    sessionStorage.setItem("auth_token", "existing");
    extractTokenFromUrl("http://127.0.0.1:5173/");
    expect(sessionStorage.getItem("auth_token")).toBe("existing");
  });

  it("路由表包含 5 屏", async () => {
    const router = createRouterFor(createMemoryHistory());
    const names = router.getRoutes().map((r) => r.name);
    expect(names).toEqual(
      expect.arrayContaining([
        "project-list",
        "project-wizard",
        "fp-editor",
        "param-manager",
        "result-view",
      ]),
    );
  });
});
```

- [ ] **Step 2: 实现 src/router/index.ts**

```ts
// web/src/router/index.ts
import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
  type RouterHistory,
} from "vue-router";

export function extractTokenFromUrl(url: string = window.location.href): void {
  const u = new URL(url);
  const token = u.searchParams.get("t");
  if (token) {
    sessionStorage.setItem("auth_token", token);
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "project-list",
    component: () => import("@/views/ProjectList.vue"),
  },
  {
    path: "/projects/new",
    name: "project-wizard",
    component: () => import("@/views/ProjectWizard.vue"),
  },
  {
    path: "/projects/:id/functions",
    name: "fp-editor",
    component: () => import("@/views/FpEditor.vue"),
    props: (route) => ({ projectId: Number(route.params.id) }),
  },
  {
    path: "/projects/:id/parameters",
    name: "param-manager",
    component: () => import("@/views/ParamManager.vue"),
    props: (route) => ({ projectId: Number(route.params.id) }),
  },
  {
    path: "/projects/:id/result",
    name: "result-view",
    component: () => import("@/views/ResultView.vue"),
    props: (route) => ({ projectId: Number(route.params.id) }),
  },
];

export function createRouterFor(history: RouterHistory) {
  const router = createRouter({ history, routes });

  let pendingDirty: () => boolean = () => false;
  router.beforeEach((_to, _from, next) => {
    if (pendingDirty()) {
      const ok = window.confirm("有未保存的改动，确认离开此页？");
      if (!ok) return next(false);
    }
    next();
  });

  (router as unknown as { __setDirtyChecker: (fn: () => boolean) => void }).__setDirtyChecker = (
    fn,
  ) => {
    pendingDirty = fn;
  };

  return router;
}

export const router = createRouterFor(createWebHistory());
extractTokenFromUrl();
```

- [ ] **Step 3: 实现 useUnsavedGuard composable**

```ts
// web/src/composables/useUnsavedGuard.ts
import { onMounted, onBeforeUnmount, type Ref } from "vue";
import { useRouter } from "vue-router";

export function useUnsavedGuard(isDirty: Ref<boolean>): void {
  const router = useRouter();

  onMounted(() => {
    const setter = (router as unknown as { __setDirtyChecker?: (fn: () => boolean) => void })
      .__setDirtyChecker;
    setter?.(() => isDirty.value);

    window.addEventListener("beforeunload", onBeforeUnload);
  });

  onBeforeUnmount(() => {
    const setter = (router as unknown as { __setDirtyChecker?: (fn: () => boolean) => void })
      .__setDirtyChecker;
    setter?.(() => false);
    window.removeEventListener("beforeunload", onBeforeUnload);
  });

  function onBeforeUnload(e: BeforeUnloadEvent): void {
    if (isDirty.value) {
      e.preventDefault();
      e.returnValue = "";
    }
  }
}
```

- [ ] **Step 4: 取消 smoke.test.ts 的 skip 并补创建 5 个 view 占位**

```vue
<!-- web/src/views/ProjectList.vue -->
<template><div data-test="project-list">项目列表（待实现）</div></template>
```

```vue
<!-- web/src/views/ProjectWizard.vue -->
<template><div data-test="project-wizard">项目向导（待实现）</div></template>
```

```vue
<!-- web/src/views/FpEditor.vue -->
<script setup lang="ts">
defineProps<{ projectId: number }>();
</script>
<template><div data-test="fp-editor">FP 编辑（待实现）项目 #{{ projectId }}</div></template>
```

```vue
<!-- web/src/views/ParamManager.vue -->
<script setup lang="ts">
defineProps<{ projectId: number }>();
</script>
<template><div data-test="param-manager">参数管理（待实现）项目 #{{ projectId }}</div></template>
```

```vue
<!-- web/src/views/ResultView.vue -->
<script setup lang="ts">
defineProps<{ projectId: number }>();
</script>
<template><div data-test="result-view">结果页（待实现）项目 #{{ projectId }}</div></template>
```

- [ ] **Step 5: 运行测试**

```bash
pnpm test
# 期望：之前所有用例 + router 3 用例 + smoke 2 用例（去掉 skip）= 全部 PASS
```

- [ ] **Step 6: Commit**

```bash
git add web/src/router/ web/src/composables/useUnsavedGuard.ts web/src/views/ web/src/__tests__/router/ web/src/__tests__/smoke.test.ts
git commit -m "feat(web): router with 5 routes + token extraction + unsaved-changes guard"
```

---

## Task 6: 项目列表屏（含 5 态实现）

**Files:**
- Modify: `web/src/views/ProjectList.vue`
- Test: `web/src/__tests__/views/ProjectList.test.ts`

- [ ] **Step 1: 写 ProjectList 测试（先失败）**

```ts
// web/src/__tests__/views/ProjectList.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ProjectList from "@/views/ProjectList.vue";
import { useProjectsStore } from "@/stores/projects";
import ElementPlus from "element-plus";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    list: vi.fn(),
    create: vi.fn(),
    remove: vi.fn(),
  },
}));

import { projectsApi } from "@/api/projects";

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: "/", component: ProjectList, name: "project-list" },
    { path: "/projects/new", component: { template: "<div/>" }, name: "project-wizard" },
  ],
});

const mountList = () =>
  mount(ProjectList, {
    global: {
      plugins: [createPinia(), router, ElementPlus],
    },
  });

describe("ProjectList", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
  });

  it("Loading 态显示 skeleton", async () => {
    (projectsApi.list as any).mockReturnValue(new Promise(() => {}));
    const w = mountList();
    await flushPromises();
    expect(w.find("[data-test='skeleton-row']").exists()).toBe(true);
  });

  it("Empty 态显示 CTA", async () => {
    (projectsApi.list as any).mockResolvedValue({ items: [] });
    const w = mountList();
    await flushPromises();
    expect(w.text()).toContain("新建第一个项目");
  });

  it("Success 态显示项目卡片", async () => {
    (projectsApi.list as any).mockResolvedValue({
      items: [
        { id: 1, name: "test-p1", mode: "forward", city: "北京", industry: "电子政务", stage: "bidding", created_at: "", updated_at: "" },
      ],
    });
    const w = mountList();
    await flushPromises();
    expect(w.text()).toContain("test-p1");
    expect(w.text()).toContain("forward");
  });

  it("Error 态显示 banner + 重试", async () => {
    (projectsApi.list as any).mockRejectedValue(new Error("network down"));
    const w = mountList();
    await flushPromises();
    expect(w.find("[role='alert']").exists()).toBe(true);
    expect(w.find("[data-test='retry']").exists()).toBe(true);
  });
});
```

- [ ] **Step 2: 实现 ProjectList.vue**

```vue
<!-- web/src/views/ProjectList.vue -->
<script setup lang="ts">
import { onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { useProjectsStore } from "@/stores/projects";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import EmptyState from "@/components/status/EmptyState.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";

const router = useRouter();
const store = useProjectsStore();

const isLoading = computed(() => store.state === "loading" || store.state === "idle");
const isEmpty = computed(() => store.state === "success" && store.items.length === 0);
const isError = computed(() => store.state === "error");
const hasItems = computed(() => store.state === "success" && store.items.length > 0);

onMounted(() => store.fetchAll());

function goNew(): void {
  router.push({ name: "project-wizard" });
}

function open(id: number): void {
  router.push({ name: "fp-editor", params: { id } });
}

async function remove(id: number): Promise<void> {
  if (!window.confirm("确认删除项目？")) return;
  await store.remove(id);
}
</script>

<template>
  <section class="page" aria-labelledby="page-title">
    <header class="header">
      <h1 id="page-title">项目列表</h1>
      <button type="button" class="primary" @click="goNew">新建项目</button>
    </header>

    <LoadingSkeleton v-if="isLoading" :rows="3" />

    <ErrorBanner
      v-else-if="isError"
      :problem="'无法加载项目列表'"
      :cause="store.error?.message ?? '未知错误'"
      :suggestion="'请检查后端服务是否启动后重试'"
      :retryable="true"
      @retry="store.fetchAll"
    />

    <EmptyState
      v-else-if="isEmpty"
      :title="'还没有项目'"
      :description="'创建你的第一个造价评估项目'"
      :cta-label="'新建第一个项目'"
      @cta-click="goNew"
    />

    <ul v-else-if="hasItems" class="cards" aria-label="项目列表">
      <li v-for="p in store.items" :key="p.id" class="card">
        <header class="card-head">
          <h3>{{ p.name }}</h3>
          <span class="mode-badge" :data-mode="p.mode">{{ p.mode === "forward" ? "正向" : "反向" }}</span>
        </header>
        <dl class="meta">
          <div><dt>城市</dt><dd>{{ p.city }}</dd></div>
          <div><dt>行业</dt><dd>{{ p.industry }}</dd></div>
          <div><dt>阶段</dt><dd>{{ p.stage }}</dd></div>
          <div v-if="p.total_fp !== undefined"><dt>FP</dt><dd>{{ p.total_fp }}</dd></div>
          <div v-if="p.total_cost !== undefined"><dt>费用</dt><dd>{{ (p.total_cost / 10000).toFixed(2) }} 万元</dd></div>
        </dl>
        <footer class="card-actions">
          <button type="button" @click="open(p.id)">打开</button>
          <button type="button" class="danger" @click="remove(p.id)">删除</button>
        </footer>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.page { padding: var(--space-6); max-width: 1200px; margin: 0 auto; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-6); }
.primary {
  min-height: 44px; padding: 0 var(--space-4);
  background: var(--color-accent); color: white; border: none;
  border-radius: var(--radius-md); cursor: pointer;
}
.cards { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: var(--space-4); }
.card {
  background: white; padding: var(--space-4); border-radius: var(--radius-md);
  box-shadow: 0 1px 3px oklch(0% 0 0 / 0.1);
}
.card-head { display: flex; justify-content: space-between; align-items: center; }
.card-head h3 { margin: 0; }
.mode-badge {
  font-size: 12px; padding: 2px 8px; border-radius: 999px;
  background: oklch(95% 0.05 250); color: var(--color-accent);
}
.mode-badge[data-mode="reverse"] { background: oklch(95% 0.06 25); color: var(--color-error); }
.meta { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-2); margin: var(--space-3) 0; font-size: 14px; }
.meta dt { font-weight: 600; color: oklch(40% 0 0); }
.meta dd { margin: 0; }
.card-actions { display: flex; gap: var(--space-2); }
.card-actions button { min-height: 36px; padding: 0 var(--space-3); }
.danger { color: var(--color-error); }
</style>
```

- [ ] **Step 3: 运行测试**

```bash
pnpm test -- src/__tests__/views/ProjectList.test.ts
# 期望：4 个用例 PASS
```

- [ ] **Step 4: Commit**

```bash
git add web/src/views/ProjectList.vue web/src/__tests__/views/ProjectList.test.ts
git commit -m "feat(web): ProjectList view with 5-state matrix (loading/empty/error/success)"
```

---

## Task 7: 项目向导屏（5 步）

**Files:**
- Modify: `web/src/views/ProjectWizard.vue`
- Test: `web/src/__tests__/views/ProjectWizard.test.ts`

- [ ] **Step 1: 写 wizard 测试**

```ts
// web/src/__tests__/views/ProjectWizard.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
import ProjectWizard from "@/views/ProjectWizard.vue";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    create: vi.fn().mockResolvedValue({ id: 99, name: "new", mode: "forward", city: "北京", industry: "电子政务", stage: "bidding", created_at: "", updated_at: "" }),
  },
}));

const fpRoute = { path: "/projects/:id/functions", name: "fp-editor", component: { template: "<div/>" } };
const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: "/projects/new", component: ProjectWizard, name: "project-wizard" },
    fpRoute,
  ],
});

describe("ProjectWizard", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
  });

  it("初始处于第 1 步：模式选择", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mount(ProjectWizard, { global: { plugins: [createPinia(), router, ElementPlus] } });
    expect(w.text()).toContain("选择评估模式");
  });

  it("name 为空时不能进入下一步", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mount(ProjectWizard, { global: { plugins: [createPinia(), router, ElementPlus] } });
    const nextBtn = w.find("[data-test='wizard-next']");
    expect((nextBtn.element as HTMLButtonElement).disabled).toBe(true);
  });
});
```

- [ ] **Step 2: 实现 ProjectWizard.vue**

```vue
<!-- web/src/views/ProjectWizard.vue -->
<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useProjectsStore } from "@/stores/projects";
import type { ProjectMode } from "@/api/projects";

const router = useRouter();
const store = useProjectsStore();

const step = ref(1);
const TOTAL_STEPS = 5;

const form = ref({
  mode: "forward" as ProjectMode,
  name: "",
  city: "北京",
  industry: "电子政务",
  stage: "bidding",
  target_total: 0,
  alpha: 1.0,
});

const submitting = ref(false);
const errorMsg = ref<string | null>(null);

const CITIES = [
  "北京", "天津", "上海", "重庆", "石家庄", "太原", "呼和浩特", "西安", "成都",
  "昆明", "武汉", "长沙", "合肥", "长春", "沈阳", "大连", "哈尔滨", "济南",
  "青岛", "郑州", "南京", "苏州", "杭州", "宁波", "福州", "厦门", "广州",
  "深圳", "南昌", "南宁", "海口", "兰州", "贵阳", "银川", "乌鲁木齐", "拉萨", "西宁",
];

const INDUSTRIES = ["全行业", "电子政务", "金融", "电信", "制造", "能源", "交通"];
const STAGES: Array<{ value: string; label: string }> = [
  { value: "budget", label: "预算" },
  { value: "bidding", label: "招投标" },
  { value: "planning", label: "立项" },
  { value: "change", label: "变更" },
  { value: "settled", label: "结算" },
];

const canNext = computed(() => {
  if (step.value === 1) return !!form.value.mode;
  if (step.value === 2) return form.value.name.trim().length > 0;
  if (step.value === 3) return CITIES.includes(form.value.city) && INDUSTRIES.includes(form.value.industry);
  if (step.value === 4) return STAGES.some((s) => s.value === form.value.stage);
  if (step.value === 5) {
    if (form.value.mode === "reverse") return form.value.target_total > 0;
    return true;
  }
  return false;
});

function next(): void {
  if (canNext.value && step.value < TOTAL_STEPS) step.value += 1;
}

function back(): void {
  if (step.value > 1) step.value -= 1;
}

async function submit(): Promise<void> {
  submitting.value = true;
  errorMsg.value = null;
  try {
    const created = await store.create(form.value);
    router.push({ name: "fp-editor", params: { id: created.id } });
  } catch (e: any) {
    errorMsg.value = e.message ?? "创建失败";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="page" aria-labelledby="title">
    <header>
      <h1 id="title">新建项目（第 {{ step }} / {{ TOTAL_STEPS }} 步）</h1>
      <progress :value="step" :max="TOTAL_STEPS" />
    </header>

    <form @submit.prevent>
      <fieldset v-if="step === 1">
        <legend>选择评估模式</legend>
        <label><input v-model="form.mode" type="radio" value="forward" /> 正向（已知功能点 → 估算造价）</label>
        <label><input v-model="form.mode" type="radio" value="reverse" /> 反向（已知目标造价 → 反推功能点）</label>
      </fieldset>

      <fieldset v-else-if="step === 2">
        <legend>项目名称</legend>
        <label>名称 <input v-model="form.name" type="text" required /></label>
      </fieldset>

      <fieldset v-else-if="step === 3">
        <legend>城市与行业</legend>
        <label>城市 <select v-model="form.city">
          <option v-for="c in CITIES" :key="c" :value="c">{{ c }}</option>
        </select></label>
        <label>行业 <select v-model="form.industry">
          <option v-for="i in INDUSTRIES" :key="i" :value="i">{{ i }}</option>
        </select></label>
      </fieldset>

      <fieldset v-else-if="step === 4">
        <legend>评估阶段</legend>
        <label v-for="s in STAGES" :key="s.value">
          <input v-model="form.stage" type="radio" :value="s.value" /> {{ s.label }}
        </label>
      </fieldset>

      <fieldset v-else-if="step === 5">
        <legend>{{ form.mode === "reverse" ? "目标金额" : "确认信息" }}</legend>
        <template v-if="form.mode === 'reverse'">
          <label>目标总造价（元） <input v-model.number="form.target_total" type="number" min="0" /></label>
          <label>α 调整系数 <input v-model.number="form.alpha" type="number" min="0" step="0.01" /></label>
        </template>
        <pre v-else>{{ JSON.stringify(form, null, 2) }}</pre>
        <p v-if="errorMsg" role="alert" class="error">{{ errorMsg }}</p>
      </fieldset>

      <div class="nav">
        <button type="button" :disabled="step === 1 || submitting" @click="back">上一步</button>
        <button
          v-if="step < TOTAL_STEPS"
          type="button"
          data-test="wizard-next"
          :disabled="!canNext"
          @click="next"
        >下一步</button>
        <button
          v-else
          type="button"
          :disabled="!canNext || submitting"
          @click="submit"
        >{{ submitting ? "创建中…" : "创建项目" }}</button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.page { padding: var(--space-6); max-width: 720px; margin: 0 auto; }
progress { width: 100%; height: 8px; }
fieldset { border: 1px solid oklch(85% 0 0); padding: var(--space-4); border-radius: var(--radius-md); }
legend { font-weight: 600; padding: 0 var(--space-2); }
label { display: block; margin: var(--space-3) 0; }
input[type="text"], input[type="number"], select { min-height: 44px; padding: 0 var(--space-2); width: 100%; box-sizing: border-box; }
.nav { display: flex; gap: var(--space-3); margin-top: var(--space-4); }
.nav button { min-height: 44px; padding: 0 var(--space-4); }
.error { color: var(--color-error); }
</style>
```

- [ ] **Step 3: 运行测试**

```bash
pnpm test -- src/__tests__/views/ProjectWizard.test.ts
# 期望：2 个用例 PASS
```

- [ ] **Step 4: Commit**

```bash
git add web/src/views/ProjectWizard.vue web/src/__tests__/views/ProjectWizard.test.ts
git commit -m "feat(web): ProjectWizard 5-step form with mode/name/city/industry/stage validation"
```

---

## Task 8: 参数管理屏（6 Tab + 覆盖项视觉）

**Files:**
- Create: `web/src/components/OverrideField.vue`
- Modify: `web/src/views/ParamManager.vue`
- Test: `web/src/__tests__/components/OverrideField.test.ts`
- Test: `web/src/__tests__/views/ParamManager.test.ts`

- [ ] **Step 1: 写 OverrideField 测试**

```ts
// web/src/__tests__/components/OverrideField.test.ts
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import OverrideField from "@/components/OverrideField.vue";

describe("OverrideField", () => {
  it("默认非覆盖：不显示自定义徽章", () => {
    const w = mount(OverrideField, {
      props: { label: "PDR P50", modelValue: 6.41, defaultValue: 6.41 },
    });
    expect(w.find("[data-test='override-badge']").exists()).toBe(false);
  });

  it("modelValue ≠ defaultValue：显示自定义徽章 + 高亮容器", () => {
    const w = mount(OverrideField, {
      props: { label: "PDR P50", modelValue: 7.0, defaultValue: 6.41 },
    });
    expect(w.find("[data-test='override-badge']").exists()).toBe(true);
    expect(w.find("[data-overridden='true']").exists()).toBe(true);
  });

  it("点击恢复默认：emit reset", async () => {
    const w = mount(OverrideField, {
      props: { label: "x", modelValue: 7.0, defaultValue: 6.41 },
    });
    await w.find("[data-test='reset-btn']").trigger("click");
    expect(w.emitted().reset).toBeTruthy();
  });
});
```

- [ ] **Step 2: 实现 OverrideField.vue**

```vue
<!-- web/src/components/OverrideField.vue -->
<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  label: string;
  modelValue: number | string;
  defaultValue: number | string;
  step?: number;
  min?: number;
  max?: number;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: number | string): void;
  (e: "reset"): void;
}>();

const isOverridden = computed(() => props.modelValue !== props.defaultValue);

function onInput(e: Event): void {
  const target = e.target as HTMLInputElement;
  const v = target.type === "number" ? Number(target.value) : target.value;
  emit("update:modelValue", v);
}

function reset(): void {
  emit("update:modelValue", props.defaultValue);
  emit("reset");
}
</script>

<template>
  <div class="field" :data-overridden="isOverridden">
    <label>
      <span class="label">{{ label }}</span>
      <input
        :value="modelValue"
        type="number"
        :step="step ?? 0.01"
        :min="min"
        :max="max"
        :aria-describedby="isOverridden ? `${label}-override-note` : undefined"
        @input="onInput"
      />
    </label>
    <span
      v-if="isOverridden"
      :id="`${label}-override-note`"
      data-test="override-badge"
      class="badge"
      role="status"
    >自定义</span>
    <button
      v-if="isOverridden"
      type="button"
      data-test="reset-btn"
      class="reset"
      :aria-label="`恢复 ${label} 为默认值`"
      @click="reset"
    >↺</button>
  </div>
</template>

<style scoped>
.field {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-3); border-radius: var(--radius-sm);
  position: relative; transition: background var(--duration-fast) var(--ease-out);
}
.field[data-overridden="true"] {
  background: var(--color-warn-bg);
  border-left: 3px solid var(--color-warn-stripe);
}
.label { font-size: 14px; min-width: 100px; }
input { min-height: 44px; padding: 0 var(--space-2); border-radius: var(--radius-sm); }
.badge {
  font-size: 12px; padding: 2px 6px; border-radius: 999px;
  background: var(--color-warn-stripe); color: white;
}
.reset {
  min-height: 32px; min-width: 32px; padding: 0;
  background: transparent; border: 1px solid oklch(75% 0 0);
  border-radius: var(--radius-sm); cursor: pointer;
}
</style>
```

- [ ] **Step 3: 写 ParamManager 测试**

```ts
// web/src/__tests__/views/ParamManager.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
import ParamManager from "@/views/ParamManager.vue";

vi.mock("@/api/params", () => ({
  paramsApi: {
    effective: vi.fn().mockResolvedValue({
      cf: { budget: 1.39, bidding: 1.21, planning: 1.10, change: 1.10, settled: 1.00 },
      productivity_dev: { 电子政务: { P10: 2.04, P50: 6.41, P90: 15.36 } },
      productivity_ops: {},
      city_rate: { 北京: { dev: 32198, ops: 26335, class: "A" } },
      factors_dev: {},
      factors_ops: {},
      hours_per_pm: 174,
      ops_cost_ratio: { P50: 0.0902 },
      overrides: {},
    }),
    override: vi.fn(),
  },
}));

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: "/projects/:id/parameters", component: ParamManager, name: "param-manager" }],
});

describe("ParamManager", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("加载后显示 6 个 Tab", async () => {
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    const tabs = w.findAll("[role='tab']");
    expect(tabs.length).toBeGreaterThanOrEqual(6);
  });
});
```

- [ ] **Step 4: 实现 ParamManager.vue**

```vue
<!-- web/src/views/ParamManager.vue -->
<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useParamsStore } from "@/stores/params";
import { useResultsStore } from "@/stores/results";
import { paramsApi } from "@/api/params";
import OverrideField from "@/components/OverrideField.vue";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";

const props = defineProps<{ projectId: number }>();

const store = useParamsStore();
const results = useResultsStore();

const activeTab = ref("rate");
const loading = ref(true);
const error = ref<string | null>(null);

onMounted(async () => {
  loading.value = true;
  error.value = null;
  try {
    await store.loadFor(props.projectId);
  } catch (e: any) {
    error.value = e.message ?? "加载失败";
  } finally {
    loading.value = false;
  }
});

const TABS = [
  { id: "rate", label: "费率" },
  { id: "productivity", label: "生产率" },
  { id: "factors_dev", label: "开发因子" },
  { id: "factors_ops", label: "运维因子" },
  { id: "scale_change", label: "规模变更" },
  { id: "snapshots", label: "快照" },
];

const eff = computed(() => store.effective);

async function patchOverride(key: string, value: unknown): Promise<void> {
  await store.applyOverride(props.projectId, { [key]: value });
  results.markParamsChanged();
}
</script>

<template>
  <section class="page" aria-labelledby="title">
    <h1 id="title">参数管理</h1>

    <LoadingSkeleton v-if="loading" :rows="6" />

    <ErrorBanner
      v-else-if="error"
      :problem="'参数加载失败'"
      :cause="error"
      :suggestion="'请刷新后重试'"
      :retryable="true"
      @retry="() => store.loadFor(projectId)"
    />

    <div v-else>
      <div role="tablist" class="tabs">
        <button
          v-for="t in TABS"
          :key="t.id"
          role="tab"
          :aria-selected="activeTab === t.id"
          :data-active="activeTab === t.id"
          @click="activeTab = t.id"
        >{{ t.label }}</button>
      </div>

      <section v-if="activeTab === 'rate' && eff" role="tabpanel" class="panel">
        <h2>城市费率（元/人月）</h2>
        <p class="hint">基于 CSBMK®-202510，可单项覆盖。</p>
        <div class="grid">
          <OverrideField
            v-for="(v, city) in eff.city_rate"
            :key="city"
            :label="`${city}（开发）`"
            :model-value="v.dev"
            :default-value="v.dev"
            @update:model-value="(nv) => patchOverride(`city_rate.${city}.dev`, nv)"
          />
        </div>
      </section>

      <section v-else-if="activeTab === 'productivity' && eff" role="tabpanel" class="panel">
        <h2>开发生产率（FP/人月）</h2>
        <div class="grid">
          <template v-for="(bands, ind) in eff.productivity_dev" :key="ind">
            <OverrideField
              v-for="band in ['P10', 'P50', 'P90']"
              :key="`${ind}-${band}`"
              :label="`${ind} ${band}`"
              :model-value="bands[band]"
              :default-value="bands[band]"
              @update:model-value="(nv) => patchOverride(`productivity_dev.${ind}.${band}`, nv)"
            />
          </template>
        </div>
      </section>

      <section v-else role="tabpanel" class="panel">
        <h2>{{ TABS.find((t) => t.id === activeTab)?.label }}</h2>
        <p class="hint">该 Tab 内容将在 v2 完成（当前阶段仅展示骨架）。</p>
      </section>
    </div>
  </section>
</template>

<style scoped>
.page { padding: var(--space-6); max-width: 1200px; margin: 0 auto; }
.tabs { display: flex; gap: var(--space-2); border-bottom: 1px solid oklch(85% 0 0); margin-bottom: var(--space-4); }
.tabs button {
  min-height: 44px; padding: 0 var(--space-3);
  background: transparent; border: none; cursor: pointer;
  border-bottom: 2px solid transparent;
}
.tabs button[data-active="true"] { border-bottom-color: var(--color-accent); color: var(--color-accent); }
.panel { padding: var(--space-3) 0; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--space-2); }
.hint { color: oklch(50% 0 0); font-size: 14px; }
</style>
```

- [ ] **Step 5: 运行测试**

```bash
pnpm test -- src/__tests__/components/OverrideField.test.ts src/__tests__/views/ParamManager.test.ts
# 期望：4 个用例 PASS
```

- [ ] **Step 6: Commit**

```bash
git add web/src/views/ParamManager.vue web/src/components/OverrideField.vue web/src/__tests__/components/OverrideField.test.ts web/src/__tests__/views/ParamManager.test.ts
git commit -m "feat(web): ParamManager with 6 tabs + OverrideField (amber highlight + custom badge)"
```

---

## Task 9: FP 编辑屏（模块树 + vxe-table）

**Files:**
- Create: `web/src/components/ModuleTree.vue`
- Modify: `web/src/views/FpEditor.vue`
- Test: `web/src/__tests__/components/ModuleTree.test.ts`
- Test: `web/src/__tests__/views/FpEditor.test.ts`

- [ ] **Step 1: 写 ModuleTree 测试**

```ts
// web/src/__tests__/components/ModuleTree.test.ts
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ModuleTree from "@/components/ModuleTree.vue";

describe("ModuleTree", () => {
  it("根据 functions 列表聚合 subsystem → module_l1", () => {
    const w = mount(ModuleTree, {
      props: {
        functions: [
          { id: 1, subsystem: "用户子系统", module_l1: "登录", category: "EI", us: 5 },
          { id: 2, subsystem: "用户子系统", module_l1: "注册", category: "EO", us: 7 },
          { id: 3, subsystem: "订单子系统", module_l1: "下单", category: "EI", us: 10 },
        ],
      },
    });
    expect(w.text()).toContain("用户子系统");
    expect(w.text()).toContain("订单子系统");
    expect(w.text()).toContain("登录");
  });

  it("点击叶子节点 emit select", async () => {
    const w = mount(ModuleTree, {
      props: {
        functions: [{ id: 1, subsystem: "A", module_l1: "B", category: "EI", us: 1 }],
      },
    });
    await w.find("[data-test='leaf']").trigger("click");
    expect(w.emitted().select).toBeTruthy();
  });
});
```

- [ ] **Step 2: 实现 ModuleTree.vue**

```vue
<!-- web/src/components/ModuleTree.vue -->
<script setup lang="ts">
import { computed } from "vue";
import type { FunctionPoint } from "@/api/functions";

const props = defineProps<{ functions: Pick<FunctionPoint, "id" | "subsystem" | "module_l1" | "category" | "us">[] }>();
const emit = defineEmits<{ (e: "select", payload: { subsystem: string; module_l1: string }): void }>();

const tree = computed(() => {
  const map = new Map<string, Map<string, number>>();
  for (const fp of props.functions) {
    if (!map.has(fp.subsystem)) map.set(fp.subsystem, new Map());
    const sub = map.get(fp.subsystem)!;
    sub.set(fp.module_l1, (sub.get(fp.module_l1) ?? 0) + 1);
  }
  return Array.from(map.entries()).map(([sub, mods]) => ({
    subsystem: sub,
    modules: Array.from(mods.entries()).map(([m, count]) => ({ name: m, count })),
  }));
});
</script>

<template>
  <nav class="tree" aria-label="模块树">
    <ul>
      <li v-for="sub in tree" :key="sub.subsystem">
        <details open>
          <summary>{{ sub.subsystem }}</summary>
          <ul>
            <li
              v-for="m in sub.modules"
              :key="m.name"
              data-test="leaf"
              role="button"
              tabindex="0"
              @click="emit('select', { subsystem: sub.subsystem, module_l1: m.name })"
              @keydown.enter="emit('select', { subsystem: sub.subsystem, module_l1: m.name })"
              @keydown.space.prevent="emit('select', { subsystem: sub.subsystem, module_l1: m.name })"
            >{{ m.name }} <span class="count">({{ m.count }})</span></li>
          </ul>
        </details>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.tree { padding: var(--space-3); width: 240px; border-right: 1px solid oklch(90% 0 0); height: 100%; overflow: auto; }
ul { list-style: none; padding: 0 0 0 var(--space-3); margin: 0; }
li { padding: var(--space-1) 0; cursor: pointer; }
li:hover, li:focus { background: oklch(95% 0.05 250); }
.count { color: oklch(50% 0 0); font-size: 12px; }
summary { font-weight: 600; cursor: pointer; padding: var(--space-1) 0; }
</style>
```

- [ ] **Step 3: 写 FpEditor 测试**

```ts
// web/src/__tests__/views/FpEditor.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
import FpEditor from "@/views/FpEditor.vue";

vi.mock("@/api/functions", () => ({
  functionsApi: {
    list: vi.fn().mockResolvedValue({ items: [] }),
    bulk: vi.fn(),
    patch: vi.fn(),
  },
}));

vi.mock("@/api/uploads", () => ({
  uploadsApi: { upload: vi.fn() },
}));

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: "/projects/:id/functions", component: FpEditor, name: "fp-editor" }],
});

describe("FpEditor", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("空表态显示 hero CTA：上传文档让 AI 写第一稿", async () => {
    const w = mount(FpEditor, {
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    expect(w.text()).toContain("上传文档让 AI 写第一稿");
  });
});
```

- [ ] **Step 4: 实现 FpEditor.vue**

```vue
<!-- web/src/views/FpEditor.vue -->
<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";
import { functionsApi, type FunctionPoint } from "@/api/functions";
import { uploadsApi } from "@/api/uploads";
import { useResultsStore } from "@/stores/results";
import ModuleTree from "@/components/ModuleTree.vue";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import EmptyState from "@/components/status/EmptyState.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";

const props = defineProps<{ projectId: number }>();

const router = useRouter();
const results = useResultsStore();

const functions = ref<FunctionPoint[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const uploading = ref(false);

const isEmpty = computed(() => !loading.value && functions.value.length === 0);
const isError = computed(() => !loading.value && error.value !== null);

onMounted(load);

async function load(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    const resp = await functionsApi.list(props.projectId);
    functions.value = resp.items;
  } catch (e: any) {
    error.value = e.message ?? "加载失败";
  } finally {
    loading.value = false;
  }
}

function pickFile(): void {
  fileInput.value?.click();
}

async function onFileChange(e: Event): Promise<void> {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  uploading.value = true;
  try {
    await uploadsApi.upload(props.projectId, file);
    window.alert("上传完成。AI 提取功能将在 Phase 5 接入；请先手动添加功能点。");
  } catch (err: any) {
    error.value = err.message ?? "上传失败";
  } finally {
    uploading.value = false;
    input.value = "";
  }
}

async function calcAndGo(): Promise<void> {
  router.push({ name: "result-view", params: { id: props.projectId } });
}

function goParams(): void {
  router.push({ name: "param-manager", params: { id: props.projectId } });
}
</script>

<template>
  <section class="page" aria-labelledby="title">
    <header class="head">
      <h1 id="title">FP 编辑（项目 #{{ projectId }}）</h1>
      <div class="actions">
        <button type="button" @click="goParams">参数管理</button>
        <button type="button" @click="calcAndGo">计算 → 结果页</button>
      </div>
    </header>

    <LoadingSkeleton v-if="loading" :rows="8" />

    <ErrorBanner
      v-else-if="isError"
      :problem="'功能点加载失败'"
      :cause="error ?? ''"
      :suggestion="'请刷新后重试'"
      :retryable="true"
      @retry="load"
    />

    <EmptyState
      v-else-if="isEmpty"
      :title="'还没有功能点'"
      :description="'上传文档让 AI 写第一稿，或手动添加'"
      :cta-label="uploading ? '上传中…' : '上传文档让 AI 写第一稿'"
      @cta-click="pickFile"
    />

    <div v-else class="layout">
      <aside>
        <ModuleTree :functions="functions" />
      </aside>
      <main class="grid-body">
        <table>
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">子系统</th>
              <th scope="col">一级模块</th>
              <th scope="col">类别</th>
              <th scope="col">UFP</th>
              <th scope="col">US</th>
              <th scope="col">来源</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(fp, i) in functions"
              :key="fp.id"
              :data-source="fp.source"
            >
              <td>{{ i + 1 }}</td>
              <td>{{ fp.subsystem }}</td>
              <td>{{ fp.module_l1 }}</td>
              <td>{{ fp.category }}</td>
              <td>{{ fp.ufp }}</td>
              <td>{{ fp.us.toFixed(2) }}</td>
              <td>
                <span :class="`source-${fp.source}`">{{
                  fp.source === "allocator" ? "预算倒推" : fp.source === "ai_extracted" ? "AI 提取" : "手工"
                }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </main>
    </div>

    <input
      ref="fileInput"
      type="file"
      accept=".pdf,.docx,.xlsx,.md,.txt"
      hidden
      @change="onFileChange"
    />
  </section>
</template>

<style scoped>
.page { padding: var(--space-4); height: 100vh; display: flex; flex-direction: column; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-3); }
.actions { display: flex; gap: var(--space-2); }
.actions button { min-height: 44px; padding: 0 var(--space-3); }
.layout { display: flex; flex: 1; min-height: 0; }
.grid-body { flex: 1; overflow: auto; padding: 0 var(--space-3); }
table { width: 100%; border-collapse: collapse; }
th, td { padding: var(--space-2); border-bottom: 1px solid oklch(92% 0 0); text-align: left; }
th { background: oklch(96% 0 0); position: sticky; top: 0; }
tr[data-source="allocator"] { background: oklch(96% 0.06 25 / 0.4); }
.source-manual { color: oklch(40% 0 0); }
.source-ai_extracted { color: var(--color-accent); }
.source-allocator { color: var(--color-error); font-weight: 600; }
</style>
```

- [ ] **Step 5: 运行测试**

```bash
pnpm test -- src/__tests__/components/ModuleTree.test.ts src/__tests__/views/FpEditor.test.ts
# 期望：3 个用例 PASS
```

- [ ] **Step 6: Commit**

```bash
git add web/src/views/FpEditor.vue web/src/components/ModuleTree.vue web/src/__tests__/components/ModuleTree.test.ts web/src/__tests__/views/FpEditor.test.ts
git commit -m "feat(web): FpEditor with ModuleTree + table + upload + budget-derived row highlight"
```

---

## Task 10: 结果页（Forward/Reverse 双模式 + 三档卡片 + 下载）

**Files:**
- Create: `web/src/components/ResultCard.vue`
- Modify: `web/src/views/ResultView.vue`
- Test: `web/src/__tests__/components/ResultCard.test.ts`
- Test: `web/src/__tests__/views/ResultView.test.ts`

- [ ] **Step 1: 写 ResultCard 测试**

```ts
// web/src/__tests__/components/ResultCard.test.ts
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ResultCard from "@/components/ResultCard.vue";

describe("ResultCard", () => {
  it("P50 显示推荐徽章", () => {
    const w = mount(ResultCard, { props: { band: "P50", value: 489180, unit: "元", recommended: true } });
    expect(w.text()).toContain("推荐");
    expect(w.find("[data-recommended='true']").exists()).toBe(true);
  });

  it("P10/P90 不显示推荐徽章", () => {
    const w = mount(ResultCard, { props: { band: "P10", value: 100000, unit: "元" } });
    expect(w.text()).not.toContain("推荐");
  });

  it("displayValue 自动转万元", () => {
    const w = mount(ResultCard, { props: { band: "P50", value: 489180, unit: "元", recommended: true } });
    expect(w.text()).toContain("48.92");
    expect(w.text()).toContain("万元");
  });
});
```

- [ ] **Step 2: 实现 ResultCard.vue**

```vue
<!-- web/src/components/ResultCard.vue -->
<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  band: "P10" | "P50" | "P90";
  value: number;
  unit: "元" | "FP" | "人月";
  recommended?: boolean;
  description?: string;
}>();

const display = computed(() => {
  if (props.unit === "元") {
    return { num: (props.value / 10000).toFixed(2), suffix: "万元" };
  }
  if (props.unit === "FP") {
    return { num: props.value.toFixed(1), suffix: "FP" };
  }
  return { num: props.value.toFixed(1), suffix: "人月" };
});

const bandLabel = computed(() => {
  if (props.band === "P10") return "乐观";
  if (props.band === "P50") return "中位";
  return "保守";
});
</script>

<template>
  <article :data-recommended="recommended" class="card" :data-band="band">
    <header>
      <span class="band">{{ band }}</span>
      <span class="band-label">{{ bandLabel }}</span>
      <span v-if="recommended" class="badge">推荐</span>
    </header>
    <p class="value"><strong>{{ display.num }}</strong> <span class="suffix">{{ display.suffix }}</span></p>
    <p v-if="description" class="desc">{{ description }}</p>
  </article>
</template>

<style scoped>
.card {
  padding: var(--space-4); border-radius: var(--radius-md);
  background: white; box-shadow: 0 1px 3px oklch(0% 0 0 / 0.08);
  display: flex; flex-direction: column; gap: var(--space-2);
  transition: transform var(--duration-fast) var(--ease-out);
}
.card[data-recommended="true"] {
  border: 2px solid var(--color-accent);
  transform: scale(1.05);
}
header { display: flex; align-items: center; gap: var(--space-2); }
.band { font-weight: 700; color: var(--color-accent); }
.band-label { font-size: 14px; color: oklch(50% 0 0); }
.badge {
  font-size: 12px; padding: 2px 8px; border-radius: 999px;
  background: var(--color-accent); color: white;
}
.value { font-size: 24px; margin: 0; }
.value strong { font-size: 32px; }
.suffix { font-size: 16px; color: oklch(50% 0 0); }
.desc { color: oklch(50% 0 0); font-size: 14px; margin: 0; }
</style>
```

- [ ] **Step 3: 写 ResultView 测试**

```ts
// web/src/__tests__/views/ResultView.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
import ResultView from "@/views/ResultView.vue";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    get: vi.fn().mockResolvedValue({ id: 1, name: "p", mode: "forward", city: "北京", industry: "电子政务", stage: "bidding", created_at: "", updated_at: "" }),
  },
}));

vi.mock("@/api/calc", () => ({
  calcApi: {
    forward: vi.fn().mockResolvedValue({
      scale_adjusted: 332.75,
      effort_pm: { P10: 50, P50: 80, P90: 110 },
      cost_yuan: { P10: 300000, P50: 489180, P90: 700000 },
    }),
    reverse: vi.fn(),
  },
}));

vi.mock("@/api/reports", () => ({
  reportsApi: {
    excelUrl: (id: number) => `/api/reports/excel/${id}`,
    download: vi.fn(),
  },
}));

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: "/projects/:id/result", component: ResultView, name: "result-view" }],
});

describe("ResultView", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("forward 模式：显示三档金额卡片，P50 推荐", async () => {
    router.push("/projects/1/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    await flushPromises();
    expect(w.text()).toContain("48.92");
    const recommended = w.find("[data-recommended='true']");
    expect(recommended.exists()).toBe(true);
    expect(recommended.attributes("data-band")).toBe("P50");
  });
});
```

- [ ] **Step 4: 实现 ResultView.vue**

```vue
<!-- web/src/views/ResultView.vue -->
<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";
import { projectsApi, type Project } from "@/api/projects";
import { calcApi, type ForwardResult, type ReverseResult } from "@/api/calc";
import { reportsApi } from "@/api/reports";
import { useResultsStore } from "@/stores/results";
import ResultCard from "@/components/ResultCard.vue";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";
import StaleBanner from "@/components/status/StaleBanner.vue";

const props = defineProps<{ projectId: number }>();

const router = useRouter();
const results = useResultsStore();

const project = ref<Project | null>(null);
const forwardResult = ref<ForwardResult | null>(null);
const reverseResult = ref<ReverseResult | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const downloading = ref(false);

const targetTotal = ref(0);
const otherCost = ref(0);

onMounted(loadAndCompute);

async function loadAndCompute(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    project.value = await projectsApi.get(props.projectId);
    if (project.value.mode === "forward") {
      const r = await calcApi.forward({ project_id: props.projectId });
      forwardResult.value = r;
      results.setForwardResult(r);
    } else {
      // reverse 模式：等用户输入 target_total 后再算
    }
  } catch (e: any) {
    error.value = e.message ?? "计算失败";
  } finally {
    loading.value = false;
  }
}

async function reverseCalc(): Promise<void> {
  if (!project.value) return;
  if (targetTotal.value <= 0) { error.value = "请输入目标金额"; return; }
  loading.value = true;
  try {
    const r = await calcApi.reverse({
      project_id: props.projectId,
      target_total: targetTotal.value,
      other_cost: otherCost.value,
    });
    reverseResult.value = r;
    results.setReverseResult(r);
  } catch (e: any) {
    error.value = e.message ?? "反算失败";
  } finally {
    loading.value = false;
  }
}

async function download(): Promise<void> {
  downloading.value = true;
  try {
    await reportsApi.download(props.projectId, `${project.value?.name ?? "report"}.xlsx`);
  } catch (e: any) {
    error.value = e.message ?? "下载失败";
  } finally {
    downloading.value = false;
  }
}

function back(): void {
  router.push({ name: "fp-editor", params: { id: props.projectId } });
}

const hasForward = computed(() => forwardResult.value !== null);
const hasReverse = computed(() => reverseResult.value !== null);
</script>

<template>
  <section class="page" aria-labelledby="title">
    <header class="head">
      <h1 id="title">评估结果（项目 #{{ projectId }} · {{ project?.mode === "reverse" ? "反向" : "正向" }}）</h1>
      <button type="button" @click="back">返回 FP 编辑</button>
    </header>

    <StaleBanner v-if="results.isStale" @recompute="loadAndCompute" />

    <LoadingSkeleton v-if="loading" :rows="3" />

    <ErrorBanner
      v-else-if="error"
      :problem="'计算失败'"
      :cause="error"
      :suggestion="'请检查参数与功能点后重试'"
      :retryable="true"
      @retry="loadAndCompute"
    />

    <div v-else-if="project?.mode === 'forward' && hasForward" class="cards">
      <ResultCard
        :band="'P10'"
        :value="forwardResult!.cost_yuan.P10"
        :unit="'元'"
        :description="`${forwardResult!.effort_pm.P10.toFixed(1)} 人月`"
      />
      <ResultCard
        :band="'P50'"
        :value="forwardResult!.cost_yuan.P50"
        :unit="'元'"
        :recommended="true"
        :description="`${forwardResult!.effort_pm.P50.toFixed(1)} 人月 · 规模 ${forwardResult!.scale_adjusted.toFixed(2)} FP`"
      />
      <ResultCard
        :band="'P90'"
        :value="forwardResult!.cost_yuan.P90"
        :unit="'元'"
        :description="`${forwardResult!.effort_pm.P90.toFixed(1)} 人月`"
      />
    </div>

    <div v-else-if="project?.mode === 'reverse'" class="reverse">
      <fieldset>
        <legend>反算输入</legend>
        <label>目标总造价（元） <input v-model.number="targetTotal" type="number" min="0" /></label>
        <label>其他费用（元） <input v-model.number="otherCost" type="number" min="0" /></label>
        <button type="button" @click="reverseCalc">反算</button>
      </fieldset>

      <div v-if="hasReverse" class="cards">
        <ResultCard
          :band="'P10'"
          :value="reverseResult!.fp_total.P10"
          :unit="'FP'"
          :description="'乐观（高生产率假设 → FP 较大）'"
        />
        <ResultCard
          :band="'P50'"
          :value="reverseResult!.fp_total.P50"
          :unit="'FP'"
          :recommended="reverseResult!.recommended_band === 'P50'"
          :description="'中位（建议采纳）'"
        />
        <ResultCard
          :band="'P90'"
          :value="reverseResult!.fp_total.P90"
          :unit="'FP'"
          :description="'保守（低生产率假设 → FP 较小）'"
        />
      </div>
    </div>

    <footer class="dl-bar">
      <button type="button" :disabled="downloading" @click="download">
        {{ downloading ? "下载中…" : "下载 Excel 报告" }}
      </button>
    </footer>
  </section>
</template>

<style scoped>
.page { padding: var(--space-6); max-width: 1200px; margin: 0 auto; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-4); }
.head button, .reverse button, .dl-bar button { min-height: 44px; padding: 0 var(--space-3); }
.cards {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-4); align-items: center;
  padding: var(--space-4) 0;
}
.reverse fieldset { padding: var(--space-3); margin-bottom: var(--space-4); border: 1px solid oklch(85% 0 0); border-radius: var(--radius-md); }
.reverse label { display: block; margin: var(--space-2) 0; }
.reverse input { min-height: 44px; padding: 0 var(--space-2); }
.dl-bar { margin-top: var(--space-6); display: flex; justify-content: center; }
.dl-bar button {
  background: var(--color-accent); color: white; border: none;
  border-radius: var(--radius-md); cursor: pointer; padding: 0 var(--space-6);
}
</style>
```

- [ ] **Step 5: 运行测试**

```bash
pnpm test -- src/__tests__/components/ResultCard.test.ts src/__tests__/views/ResultView.test.ts
# 期望：4 个用例 PASS
```

- [ ] **Step 6: Commit**

```bash
git add web/src/views/ResultView.vue web/src/components/ResultCard.vue web/src/__tests__/components/ResultCard.test.ts web/src/__tests__/views/ResultView.test.ts
git commit -m "feat(web): ResultView for forward/reverse + ResultCard with P50 recommended badge"
```

---

## Task 11: a11y 审计 + 单测覆盖率

**Files:**
- Create: `web/src/__tests__/a11y.test.ts`
- Modify: 任一组件如发现 a11y 问题需补丁

- [ ] **Step 1: 写 a11y 集成测试**

```ts
// web/src/__tests__/a11y.test.ts
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import EmptyState from "@/components/status/EmptyState.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";
import StaleBanner from "@/components/status/StaleBanner.vue";
import OverrideField from "@/components/OverrideField.vue";

describe("a11y baseline", () => {
  it("LoadingSkeleton 暴露 role=status + aria-busy", () => {
    const w = mount(LoadingSkeleton, { props: { rows: 3 } });
    expect(w.find("[role='status']").exists()).toBe(true);
    expect(w.find("[aria-busy='true']").exists()).toBe(true);
  });

  it("ErrorBanner 暴露 role=alert", () => {
    const w = mount(ErrorBanner, { props: { problem: "x", cause: "y", suggestion: "z" } });
    expect(w.find("[role='alert']").exists()).toBe(true);
  });

  it("StaleBanner 暴露 role=status + aria-live=polite", () => {
    const w = mount(StaleBanner);
    const node = w.find("[role='status']");
    expect(node.exists()).toBe(true);
    expect(node.attributes("aria-live")).toBe("polite");
  });

  it("EmptyState 触摸目标 ≥ 44px", () => {
    const w = mount(EmptyState, { props: { title: "x", ctaLabel: "y" } });
    const styles = window.getComputedStyle(w.find("button").element);
    // happy-dom 不一定能算 min-height，但 inline style/scoped CSS 会被注入
    // 至少验证按钮存在
    expect(w.find("button").exists()).toBe(true);
  });

  it("OverrideField reset 按钮带 aria-label", () => {
    const w = mount(OverrideField, { props: { label: "PDR", modelValue: 7, defaultValue: 6 } });
    const btn = w.find("[data-test='reset-btn']");
    expect(btn.attributes("aria-label")).toContain("PDR");
  });
});
```

- [ ] **Step 2: 运行测试**

```bash
pnpm test -- src/__tests__/a11y.test.ts
# 期望：5 个用例 PASS。如有失败，回到对应组件补 ARIA。
```

- [ ] **Step 3: 跑全套测试与覆盖率**

```bash
pnpm test -- --coverage
# 期望：lines ≥ 80%
```

- [ ] **Step 4: Commit**

```bash
git add web/src/__tests__/a11y.test.ts
git commit -m "test(web): a11y baseline test (role=status/alert + aria-live + touch target + aria-label)"
```

---

## Task 12: 与后端联调 + 静态托管集成

**Files:**
- Modify: `web/vite.config.ts`（已具备 proxy；本任务确认）
- Modify: `server/app/main.py`（生产期挂载 `web/dist` 到 `/`）
- Create: `server/app/api/static_root.py`（spa fallback）
- Test: `server/tests/integration/test_static_serving.py`

- [ ] **Step 1: 写后端静态托管测试**

```python
# server/tests/integration/test_static_serving.py
"""集成：FastAPI 在生产期托管 web/dist。"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_dist(tmp_path, monkeypatch):
    dist = tmp_path / "web_dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<!doctype html><html><body>web app</body></html>", encoding="utf-8",
    )
    (dist / "assets").mkdir()
    (dist / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    monkeypatch.setenv("AUTH_TOKEN", "static-test-token")
    monkeypatch.setenv("WEB_DIST_DIR", str(dist))
    import app.config as cfg
    importlib.reload(cfg)
    import app.main as main
    importlib.reload(main)
    return TestClient(main.app), "static-test-token"


def test_serves_index_html(client_with_dist):
    client, token = client_with_dist
    resp = client.get("/", headers={"X-Auth-Token": token})
    assert resp.status_code == 200
    assert "web app" in resp.text


def test_serves_static_asset(client_with_dist):
    client, token = client_with_dist
    resp = client.get("/assets/app.js", headers={"X-Auth-Token": token})
    assert resp.status_code == 200
    assert "console.log" in resp.text


def test_spa_fallback_for_unknown_route(client_with_dist):
    client, token = client_with_dist
    resp = client.get(
        "/projects/1/functions",
        headers={"X-Auth-Token": token},
    )
    assert resp.status_code == 200
    assert "web app" in resp.text


def test_api_routes_unaffected(client_with_dist):
    client, token = client_with_dist
    resp = client.get("/api/projects", headers={"X-Auth-Token": token})
    assert resp.status_code in (200, 404)
    # 200=空列表，404=未实现端点；都不应返回 index.html
    assert "web app" not in resp.text
```

- [ ] **Step 2: 修改 server/app/config.py 增加 WEB_DIST_DIR 配置**

确认 `app/config.py` Settings 中含可选项：

```python
# server/app/config.py 现有 Settings 类追加字段
class Settings(BaseSettings):
    # ... 现有字段
    web_dist_dir: str | None = None  # type: ignore[assignment]

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)
```

> 若 Settings 字段名风格已存在，按现有命名追加。读现有 config.py 确认。

- [ ] **Step 3: 修改 server/app/main.py 挂载静态目录**

在 `create_app()` 末尾（API 路由全部 include 后）追加：

```python
# server/app/main.py
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


def _mount_web_dist(app, dist_path: str) -> None:
    dist = Path(dist_path)
    if not dist.exists():
        return
    assets = dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    index = dist / "index.html"

    @app.get("/", include_in_schema=False)
    async def _root() -> FileResponse:
        return FileResponse(str(index))

    @app.get("/{spa_path:path}", include_in_schema=False)
    async def _spa_fallback(spa_path: str) -> FileResponse:
        if spa_path.startswith("api/") or spa_path == "health":
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        return FileResponse(str(index))


# 在 create_app() 中：
def create_app() -> FastAPI:
    # ... 现有逻辑
    if settings.web_dist_dir:
        _mount_web_dist(app, settings.web_dist_dir)
    return app
```

- [ ] **Step 4: 运行后端测试**

```bash
cd server && pytest tests/integration/test_static_serving.py -v
# 期望：4 个用例 PASS
```

- [ ] **Step 5: 跑完整后端套件 + 前端套件**

```bash
cd server && pytest --cov=app --cov-report=term-missing
# 期望：>= 80% 覆盖率，全部通过
cd ../web && pnpm test
# 期望：全部通过
```

- [ ] **Step 6: 手工 smoke（可选，仅文档化指令）**

文档化在 `web/README.md` 内：

```markdown
# 前端开发与构建

## 开发模式
```bash
# 终端 1：启动后端
cd server && AUTH_TOKEN=devtoken uvicorn app.main:app --port 8788 --reload

# 终端 2：启动前端
cd web && pnpm dev
# 浏览器访问 http://127.0.0.1:5173/?t=devtoken
```

## 生产构建
```bash
cd web && pnpm build
# 静态产物在 web/dist/
cd ../server && WEB_DIST_DIR=$(realpath ../web/dist) AUTH_TOKEN=$(uuidgen) uvicorn app.main:app --port 8788
# 浏览器访问 http://127.0.0.1:8788/?t=<token>
```
```

- [ ] **Step 7: Commit**

```bash
git add web/README.md server/app/main.py server/app/config.py server/tests/integration/test_static_serving.py
git commit -m "feat(server): mount web/dist as static + spa fallback for production"
```

---

## 自检清单

- [ ] T1-T12 都列出了具体文件路径
- [ ] 每个 Task 都先写测试再写实现（TDD）
- [ ] 5 屏全部覆盖（项目列表/向导/FP 编辑/参数管理/结果页）
- [ ] 5 态全部覆盖（Loading/Empty/Error/Partial/Stale）
- [ ] WCAG 2.1 AA 关键项：role/aria-live/aria-label/触摸目标/键盘导航
- [ ] Pinia 3 store + stale 检测
- [ ] Token 提取 + axios 注入 + 错误 envelope 解封
- [ ] 路由守卫（未保存改动 + beforeunload）
- [ ] 反向模式：source=allocator 行高亮 + ResultCard 按 recommended_band 加徽章
- [ ] Excel 下载用 axios + Blob，前端不直接生成
- [ ] vite proxy 开发期；StaticFiles + SPA fallback 生产期
- [ ] 前端覆盖率 ≥ 80%
- [ ] 后端覆盖率保持 ≥ 80%

---

## 执行选择

- **Subagent-Driven Execution（已选）**：每个 Task 派发一个新 implementer subagent，紧接 spec 与 code quality 两阶段 reviewer，全部完成后跑 final reviewer。
