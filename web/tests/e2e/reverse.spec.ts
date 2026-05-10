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

      // 3. 填入目标金额并反算
      await page.getByLabel(/目标总造价/).fill("500000");
      await page.getByLabel(/其他费用/).fill("50000");
      await page.getByRole("button", { name: /^反算$/ }).click();

      // 4. 三档 FP 卡片
      await expect(page.locator("[data-band]")).toHaveCount(3);
      await expect(page.locator("[data-band='P10']")).toContainText(/FP/);
      await expect(page.locator("[data-band='P50']")).toContainText(/FP/);
      await expect(page.locator("[data-band='P90']")).toContainText(/FP/);
    } finally {
      // teardown
      await request.delete(`${baseURL}/api/projects/${id}`, {
        headers: { "X-Auth-Token": TOKEN },
      });
    }
  });
});
