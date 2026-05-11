/**
 * T4 — v2.3 AiTaskModal E2E Polling
 *
 * 通过 HTTP API 模拟 plugin 行为，验证 AiTaskModal 显示进度从 running → done。
 *
 * 步骤：
 *   1. 导航到第一个项目的 FpEditor（功能点视图）
 *   2. 后台 POST /api/ai-tasks 创建任务
 *   3. PATCH 推进到 running + 30% + 日志
 *   4. 打开 AiTaskModal，验证进度条与日志文字可见
 *   5. PATCH 推进到 done 100%
 *   6. 验证"采纳 FP"按钮出现
 */
import { test, expect } from "@playwright/test";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

async function createTask(request: import("@playwright/test").APIRequestContext, baseURL: string, projectId: string): Promise<string> {
  const r = await request.post(`${baseURL}/api/ai-tasks`, {
    headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
    data: { project_id: projectId, kind: "extract" },
  });
  expect(r.status()).toBe(201);
  const body = await r.json();
  return body.id;
}

async function patchTask(
  request: import("@playwright/test").APIRequestContext,
  baseURL: string,
  taskId: string,
  payload: Record<string, unknown>,
) {
  const r = await request.patch(`${baseURL}/api/ai-tasks/${taskId}`, {
    headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
    data: payload,
  });
  expect(r.status()).toBe(200);
}

test("AiTaskModal polling 显示进度从 running → done", async ({ page, request, baseURL }) => {
  const base = baseURL ?? "http://127.0.0.1:8788";

  // 1. 导航首页，点第一行进入项目
  await page.goto("/");
  const firstRow = page.locator("tr.row-link").first();
  await expect(firstRow).toBeVisible({ timeout: 10_000 });
  await firstRow.click();
  await page.waitForURL(/\/projects\/[^/]+\/functions/, { timeout: 15_000 });

  // 2. 从 URL 提取 projectId
  const url = page.url();
  const projectId = url.split("/projects/")[1].split("/")[0];
  expect(projectId).toBeTruthy();

  // 3. 后台创建任务
  const taskId = await createTask(request, base, projectId);

  // 4. PATCH → running 30%
  await patchTask(request, base, taskId, {
    status: "running",
    progress_pct: 30,
    stage_log_append: "✓ 章节切分",
  });

  // 5. 打开 AI 任务 modal（按钮含文案 "AI 任务"）
  await page.locator("button", { hasText: "AI 任务" }).first().click();
  await expect(page.locator(".ai-modal")).toBeVisible({ timeout: 5_000 });

  // 6. Polling 后应看到进度条 + 日志文字
  await expect(page.locator(".ai-modal-bar-fill")).toBeVisible({ timeout: 6_000 });
  await expect(page.locator(".ai-modal-log")).toContainText("章节切分", { timeout: 6_000 });

  // 7. PATCH → done 100%
  await patchTask(request, base, taskId, {
    status: "done",
    progress_pct: 100,
    stage_log_append: "✓ 完成",
  });

  // 8. "采纳 FP" 按钮在 status=done 时显示
  await expect(
    page.locator(".ai-modal button", { hasText: "采纳" }),
  ).toBeVisible({ timeout: 6_000 });
});
