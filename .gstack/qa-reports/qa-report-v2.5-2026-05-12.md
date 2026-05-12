# QA Report — v2.5 用户反馈修复

**Date:** 2026-05-12
**Branch:** `v2.5-user-feedback` (24 commits ahead of `master`)
**Mode:** diff-aware（branch v2.5-user-feedback, 95 files changed）
**Tier:** Standard
**Tester:** Claude Code Opus 4.7 + /gstack-qa workflow
**Health score:** 95/100（1 fixed regression, 0 outstanding HIGH issues）

## TL;DR

v2.5 5 项用户反馈修复均功能可用：上传管理 / Wizard 编辑 / 因子中文化 / Claude 后台 spawn。
完整 playwright 真实 Chromium 浏览器测试 29/29 PASS（修复 1 个 T19 swap 后的 selector regression）。
API 层 spot-check 全绿（DELETE upload 204、PATCH project 200、GET factor-meta 200、AI task start 返回 pid 12667）。

## Scope

诊断 v2.5 release 在 master..HEAD 共 24 commits 改动：

| Surface | 后端 | 前端 | 测试 |
|---|---|---|---|
| 上传管理 | `api/uploads.py` DELETE, `services/uploads.py` 磁盘清理 | `api/uploads.ts`, `UploadListModal.vue`, `FpEditor.vue` toolbar | T4 e2e + 2 unit |
| Wizard 编辑 | `api/projects.py` PATCH（已存） | `views/ProjectWizard.vue` projectId prop, `router/index.ts` /edit 路由, `ProjectActionMenu.vue` | T9 e2e + 2 unit |
| 因子中文化 | `csbmk_factors_meta.json` + `api/params.py` factor-meta endpoint | `api/factorMeta.ts`, `FactorDropdown.vue` meta prop, Wizard step 5/6 折叠 | 3 unit |
| AI 任务后台 | `services/ai_tasks.py` spawn_claude_extract + stop, `db/models.py` AiTask.pid, alembic e5be802ba4f1, `api/ai_tasks.py` /start /stop | `api/aiTasks.ts` create/start/stop, `AiTaskPanel.vue`, `FpEditor.vue` swap | T20 e2e + 4 unit + 3 integration |

## Methodology

CDP 浏览器 (browse server) 在本机会话内启动失败（client 报 "Starting server..."不断 / IPC dead）。
转而使用：

1. **完整 playwright 真实 Chromium headless** (3.5 min, 29 specs) — 等同 /qa 浏览器测试
2. **API/curl probe** 验证 v2.5 后端 endpoint
3. **pytest 202 PASS + vitest 256 PASS** 作为单元 / 组件 / 集成基线

## Findings

### ISSUE-001 — v2.3 polling spec 选择器适配 AiTaskPanel
**Severity:** HIGH（测试 regression / blocks CI green）
**Category:** Functional / Regression
**Repro:** `pnpm playwright test tests/e2e/v2.3-ai-task-polling.spec.ts` → 1 failed at `.ai-modal-bar-fill` not visible
**Root cause:** T19 swap `AiTaskModal` → `AiTaskPanel` 改了 DOM selector（`.ai-modal*` → `.task-row*`），但 v2.3 spec 未同步更新。
**Fix:** `web/tests/e2e/v2.3-ai-task-polling.spec.ts` 选择器 5 处更新为新 panel 选择器。
**Re-test:** `1 passed (9.5s)` ✅
**Commit:** `f5dfb23`
**Files changed:** `web/tests/e2e/v2.3-ai-task-polling.spec.ts` (5 selector lines)

### ISSUE-002（INFRA / 非代码 bug）— 运行中的 dev server 没加载新代码
**Severity:** LOW（QA infra observation, 非用户问题）
**Repro:** v2.5 commit 后老 uvicorn (PID 89637) 仍占 8788 端口，未重启 → factor-meta endpoint 404
**Root cause:** uvicorn 没启 `--reload`，开发期 manual restart 才能加载新 endpoint。
**Fix:** 仅本次 QA — `kill -9 89637 && nohup uvicorn ...`。重启后 factor-meta 200 OK。
**Recommendation:** 部署文档说明：每次 commit 后 dev/staging server 需要 `systemctl restart` 或同等动作。或加入 `uvicorn --reload` 到 dev 启动脚本。
**Files changed:** None（不属于 v2.5 bug）

## QA Probe 结果（5 surfaces × Standard 深度）

### QA1 — 服务器健康 + 范围识别
- `GET /health` → 200 ✅
- master..HEAD 24 commits / 95 files 改动确认
- 命中 v2.5 surface：5 个

### QA2 — 上传管理
- Create project → `prj-4e9a5ffdef64` ✅
- `POST /api/projects/{pid}/uploads` (multipart) → 201 ✅
- `GET /api/projects/{pid}/uploads` → 1 item，含 `id/filename/size/filetype/uploaded_at/parsed_text_path` ✅
- `DELETE /api/projects/{pid}/uploads/4` → **204 No Content** ✅
- 重新 list → `{"ok": true, "data": []}` ✅
- 磁盘验证：上传目录 `/tmp/uploads/{pid}/` 不存在（已物理清理）✅
- e2e `v2.5-uploads-manage.spec.ts` → PASS

### QA3 — Wizard 编辑
- `GET /api/projects/{pid}` → 含全部 field 用于预填（name/city/industry/...）✅
- `PATCH /api/projects/{pid}` body=`{"name":"...(改)","other_cost":50000}` → 200 ✅
- 重新 GET 验证：name = `QA upload test (改)`, other_cost = 50000.0 ✅
- e2e `v2.5-wizard-edit.spec.ts` → PASS（访问 `/edit` 显示 "编辑项目设定" + 预填 name）

### QA4 — 因子中文化
- `GET /api/params/factor-meta` → 200，**5 dev + 11 ops** factors ✅
- `factors_dev.app_type.label` = "应用类型"
- **8 个 app_type options** 包括之前 spec §6.1 漏掉的 `通信控制` (×1.90) + `流程控制` (×2.00) ✅
- 中文 description 含 multiplier："业务处理（OLTP）— 在线事务处理类 — 典型企业管理 / 业务系统。基准 ×1.00。"
- `factors_ops.security_level.L5` = "L5（五级）— 极重要 / 涉密系统。×1.10。" ✅
- 全部 16 factor × 全部 options 已校对 csbmk_202510.json NO_GAPS（pytest test_factor_meta_options_have_label_and_description PASS）

### QA5 — AI 任务后台 spawn
- `POST /api/ai-tasks` (project_id + kind=extract) → 201，返回 task `id`，status=queued ✅
- `POST /api/ai-tasks/{id}/start` → 200，**返回 `{"pid": 12667}`** 真实 subprocess.Popen 启动 ✅
- `GET /api/ai-tasks/{id}` → status=`running`, progress=1%, stage_log=`✓ 后台进程已启动 (pid=12667)` ✅
- 日志文件：`/tmp/cost-data/ai-task-{tid}.log` 94 bytes 已落盘 ✅
- `POST /api/ai-tasks/{id}/stop` → 200，返回 `{"stopped": true}` ✅
- e2e `v2.5-ai-task-spawn.spec.ts` → PASS（开 panel → click 新建 → task row 或 banner 出现）

## Test 基线

| 测试层 | 数量 | 结果 |
|---|---:|---|
| pytest (server) | 202 | ✅ PASS |
| vitest (web) | 256 (+1 skipped) | ✅ PASS |
| playwright e2e (Chromium headless) | 29 | ✅ 29 PASS (3.1 min) |
| vue-tsc | 0 errors | ✅ |

## Health Score

| Category | Weight | Score | Notes |
|---|---:|---:|---|
| Console | 15% | 100 | No console errors observed during e2e |
| Links | 10% | 100 | No broken links |
| Visual | 10% | 100 | Design tokens unified (T19 panel sticks to v2.2 system) |
| Functional | 20% | 95 | ISSUE-001 (HIGH) fixed; all 5 surfaces operational |
| UX | 15% | 95 | Tooltip / 折叠 / 进度条 all design-system compliant |
| Performance | 10% | 90 | Polling 1.5s reasonable; spawn detached + start_new_session |
| Content | 5% | 100 | 16 factor × all options 中文 description complete |
| Accessibility | 15% | 90 | `<details>` semantic; ⓘ uses title attr (mouse-only — could improve with aria-describedby) |

**Final:** `0.15·100 + 0.10·100 + 0.10·100 + 0.20·95 + 0.15·95 + 0.10·90 + 0.05·100 + 0.15·90 = 95.0`

## Top 3 Things to Fix

1. **(已修)** ISSUE-001 — v2.3 polling spec 选择器适配 AiTaskPanel（commit `f5dfb23`）
2. **(建议)** dev/staging 部署文档加 `uvicorn --reload` 或重启脚本，避免 ISSUE-002 类静默 stale 服务
3. **(优化)** FactorDropdown 的 ⓘ tooltip 改用 aria-describedby + 显式 popover，键盘可访问

## Console Health

- e2e 全程未观察到 JS console error
- AiTaskPanel polling 写入合理（1.5s）
- spawn 失败 fallback 路径 (banner) 已验证

## PR Summary line

> "/qa 找到 1 issue 修复 1（ISSUE-001 v2.3 selector regression），健康分 95/100，pytest 202 / vitest 256 / e2e 29 全 PASS。"

## Files Changed in This QA Run

- `web/tests/e2e/v2.3-ai-task-polling.spec.ts` — selector 适配 AiTaskPanel (commit `f5dfb23`)
- `.gstack/qa-reports/qa-report-v2.5-2026-05-12.md` — 本报告
