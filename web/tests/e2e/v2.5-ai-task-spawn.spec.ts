/**
 * T20 — v2.5 AI 任务面板 spawn 流程 E2E
 *
 * 验证：
 *   1. 打开 FpEditor，点 "🤖 AI 任务面板" 按钮，面板出现
 *   2. 空状态显示 "暂无任务" 提示文字
 *   3. 点 "+ 新建提取任务" 按钮
 *   4. 断言（二选一）：
 *      - claude CLI 可用 → .task-row 出现（spawn 成功）
 *      - claude CLI 不可用 → .banner-amber 出现（spawn 失败提示）
 */
import { test, expect, request } from "@playwright/test";

const BASE_URL = "http://127.0.0.1:8788";
const AUTH_TOKEN = "e2e-token";

async function createProject(): Promise<string> {
  const ctx = await request.newContext({
    baseURL: BASE_URL,
    extraHTTPHeaders: {
      "X-Auth-Token": AUTH_TOKEN,
      "content-type": "application/json",
      Origin: BASE_URL,
    },
  });
  const r = await ctx.post("/api/projects", {
    data: {
      name: `AI Task Spawn ${Date.now()}`,
      project_type: "dev_only",
      phase: "bidding",
      city: "北京",
      industry: "电子政务",
      mode: "forward",
      basis_data_ver: "CSBMK-202510",
      other_cost: 25000,
    },
  });
  expect(r.status()).toBe(201);
  const body = await r.json();
  return body.data?.id ?? body.id;
}

test("v2.5 AI 任务面板 — 列表渲染 + 启动反馈", async ({ page }) => {
  const pid = await createProject();
  await page.goto(`/projects/${pid}/functions`);
  await page.waitForLoadState("networkidle");

  // 打开 AI 任务面板（按钮文案："🤖 AI 任务面板"）
  await page.getByRole("button", { name: /AI 任务/ }).click();
  await expect(page.locator(".task-panel")).toBeVisible({ timeout: 5000 });

  // 空状态：暂无任务提示
  await expect(page.locator(".task-panel")).toContainText("暂无任务");

  // 点 "+ 新建提取任务"
  await page.locator(".task-panel button").filter({ hasText: "新建" }).click();

  // 等待 polling 或错误 banner 出现（最多 2.5s）
  await page.waitForTimeout(2500);

  // 截图备查（调试用）
  await page.screenshot({ path: "/tmp/ai-spawn.png" });

  // 任一断言成立即 PASS：
  //   - claude CLI 可用 → task row 出现（spawn 成功）
  //   - claude CLI 不可用 / spawn 失败 → banner-amber 提示
  const taskRowCount = await page.locator(".task-row").count();
  const bannerVisible = await page
    .locator(".task-panel .banner-amber")
    .isVisible()
    .catch(() => false);
  expect(taskRowCount > 0 || bannerVisible).toBe(true);
});
