# 前端开发与构建

Vue 3 + Vite 单页应用。开发期由 Vite dev server 托管 + 反向代理后端；生产期由 FastAPI 直接托管 `web/dist/`。

## 目录约定

- `src/` 应用代码（views / components / stores / api / composables）
- `src/__tests__/` Vitest 单元 + 组件测试
- `dist/` 生产构建产物（提交到仓库的 ignore；由 `pnpm build` 生成）

## 本地开发

```bash
# 终端 1：启动后端（带固定 token，便于浏览器 query 注入）
cd server
COST_AUTH_TOKEN=devtoken uvicorn app.main:app --port 8788 --reload

# 终端 2：启动前端 dev server（vite proxy 转发 /api 与 /health → 8788）
cd web
pnpm install        # 仅首次或依赖变更后
pnpm dev
```

浏览器访问：

```
http://127.0.0.1:5173/?t=devtoken
```

> token 通过 query 提取一次后由 sessionStorage 缓存（spec §9.5.1）。后续 axios 请求自动注入 `X-Auth-Token` header。

## 生产构建 + 单端口部署

```bash
# 1. 构建静态产物
cd web
pnpm build
# 产物落到 web/dist/index.html + web/dist/assets/*

# 2. 启动后端，挂载 web/dist 为静态根
cd ../server
COST_WEB_DIST_DIR=$(realpath ../web/dist) \
  COST_AUTH_TOKEN=$(uuidgen) \
  uvicorn app.main:app --port 8788
```

浏览器访问后端端口（前后端同源）：

```
http://127.0.0.1:8788/?t=<token>
```

后端行为：

- `GET /` → `web/dist/index.html`
- `GET /assets/*` → 静态资源
- `GET /<任意 SPA 深链>` → SPA fallback 返回 `index.html`（前端路由再处理）
- `GET /api/*` → REST API（仍需要 token）
- `GET /health` → 健康检查（免认证）

> 安全说明：SPA shell 与 `/assets/*` 是浏览器自发请求且无 token header，因此 token 中间件对所有非 `/api/` 的 GET 请求免认证。token 仍然保护全部 `/api/*` 路由（包括 GET 数据接口与所有写操作）。SPA shell 本身不含敏感数据。

## 常用命令

```bash
pnpm dev           # 启动 vite dev server
pnpm build         # 生产构建到 dist/
pnpm preview       # 本地预览生产产物（不会启 FastAPI 托管）
pnpm test          # 运行 Vitest 单元 + 组件测试
pnpm test --coverage   # 含覆盖率报告
pnpm type-check    # vue-tsc --noEmit
pnpm lint          # eslint，max-warnings=0
```

## 故障排查

| 现象 | 排查 |
| --- | --- |
| `pnpm dev` 后页面 401 | URL 没带 `?t=<token>`，或 sessionStorage 已缓存了过期 token；清空 storage 重试 |
| 生产构建后访问 `/projects/1` 直接 404 | 后端没挂载 SPA fallback；确认 `COST_WEB_DIST_DIR` 已设置且路径存在 |
| `/assets/app.js` 401 | 升级旧版后端；token 中间件需放行非 `/api/` GET（已在最新 `app/deps.py` 内置） |
| 浏览器控制台 CORS 报错 | 同源部署不应触发；确认你访问的是 8788 而非 5173 |

## E2E 测试

E2E 测试基于 Playwright，需要后端启动 + `web/dist` 构建产物（FastAPI 同源托管）。两个 spec：

- `tests/e2e/forward.spec.ts` — 项目列表 → FP 编辑 → 三档结果 → 下载 Excel
- `tests/e2e/reverse.spec.ts` — 反向项目 → 输入目标金额 → 反算 → 三档 FP

```bash
# 终端 1：先 build 前端
cd web
pnpm install                       # 仅首次或依赖变更
pnpm exec playwright install chromium  # 仅首次（约 120MB）
pnpm build                         # 产物落到 web/dist/

# 终端 2：启动后端（用固定 token "e2e-token"，便于浏览器拼到 URL）
cd ../server
COST_AUTH_TOKEN=e2e-token \
COST_WEB_DIST_DIR=$(realpath ../web/dist) \
COST_DATABASE_URL=sqlite:////tmp/cost-e2e.sqlite \
.venv/bin/python -m app.bootstrap \
  --db /tmp/cost-e2e.sqlite \
  --seed app/data/csbmk_202510.json
COST_AUTH_TOKEN=e2e-token \
COST_DATABASE_URL=sqlite:////tmp/cost-e2e.sqlite \
COST_WEB_DIST_DIR=$(realpath ../web/dist) \
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8788

# 终端 3：跑 e2e（E2E_AUTH_TOKEN 必须与 COST_AUTH_TOKEN 一致）
cd ../web
E2E_AUTH_TOKEN=e2e-token pnpm test:e2e

# 调试 / UI 模式
E2E_AUTH_TOKEN=e2e-token pnpm test:e2e:ui
```

> 如果 e2e 因 web/dist 未 build 报 404，先 `pnpm build`；如果因 token 不匹配 401，确认 `COST_AUTH_TOKEN` 与 `E2E_AUTH_TOKEN` 完全一致。
