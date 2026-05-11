import { test, expect } from "./fixtures";

test.describe("Reverse 模式完整流程", () => {
  test("从向导创建 reverse 项目 → 输入目标金额 → 反算 → 三档 FP", async ({
    page,
    baseURL,
    request,
  }) => {
    const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

    // 1. 创建 reverse 项目（接口创建以加快 e2e）
    const created = await request.post(`${baseURL}/api/projects`, {
      headers: { "X-Auth-Token": TOKEN },
      data: {
        name: `e2e-rev-${Date.now()}`,
        project_type: "dev_only",
        mode: "reverse",
        city: "北京",
        industry: "电子政务",
        phase: "bidding",
        basis_data_ver: "CSBMK®-202510",
      },
    });
    expect(created.ok()).toBeTruthy();
    const body = await created.json();
    const id: string = body.data.id;

    try {
      // 2. 直接进入结果页（goto 一次即可，URL 中带 token）
      await page.goto(`${baseURL}/projects/${id}/result?t=${TOKEN}`);
      await expect(page.getByText(/评估结果.*反向/)).toBeVisible();

      // 3. 填入目标金额并反算（v2.4 — 4 列 grid，label 无 for/id，用 nth 索引）
      const numInputs = page.locator("input[type='number']");
      await numInputs.nth(0).fill("500000"); // 目标总造价
      await numInputs.nth(1).fill("50000");  // 其他费用
      await page.getByRole("button", { name: /^反算$/ }).click();
      await page.waitForLoadState("networkidle");

      // 4. 三档 FP 卡片（v2.4 — ResultTrio 替代旧 ResultCard，用 .result-card-tag 区分档位）
      await expect(page.locator(".result-trio .result-card")).toHaveCount(3);
      await expect(page.locator(".result-card-tag", { hasText: "P10" }).first()).toBeVisible();
      await expect(page.locator(".result-card-tag", { hasText: "P50" }).first()).toBeVisible();
      await expect(page.locator(".result-card-tag", { hasText: "P90" }).first()).toBeVisible();
      await expect(page.locator(".result-card-amt").first()).toContainText(/FP/);
    } finally {
      // teardown
      await request.delete(`${baseURL}/api/projects/${id}`, {
        headers: { "X-Auth-Token": TOKEN },
      });
    }
  });
});
