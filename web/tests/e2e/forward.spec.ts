import { test, expect } from "./fixtures";

test.describe("Forward 模式完整流程", () => {
  test("从项目列表 → FP 编辑 → 计算结果 → 下载 Excel", async ({
    page,
    freshProject,
    baseURL,
    request,
  }) => {
    // 0. 浏览器把 token 拼到 URL
    const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";
    await page.goto(`${baseURL}/?t=${TOKEN}`);

    // 1. 项目列表能看到刚刚创建的项目
    await expect(page.getByRole("heading", { name: "项目列表" })).toBeVisible();
    await expect(page.getByText(freshProject.name)).toBeVisible();

    // 2. 跳到 FP 编辑
    const apiBulk = await request.post(
      `${baseURL}/api/projects/${freshProject.id}/functions/bulk`,
      {
        headers: { "X-Auth-Token": TOKEN },
        data: {
          items: [
            { subsystem: "用户子系统", module_l1: "登录", category: "EI", ufp: 4, reuse_ratio: 0, modify_ratio: 0, source: "manual" },
            { subsystem: "用户子系统", module_l1: "注册", category: "EI", ufp: 4, reuse_ratio: 0, modify_ratio: 0, source: "manual" },
            { subsystem: "订单子系统", module_l1: "下单", category: "EI", ufp: 4, reuse_ratio: 0, modify_ratio: 0, source: "manual" },
            { subsystem: "订单子系统", module_l1: "查询", category: "EQ", ufp: 4, reuse_ratio: 0, modify_ratio: 0, source: "manual" },
            { subsystem: "数据", module_l1: "用户", category: "ILF", ufp: 10, reuse_ratio: 0, modify_ratio: 0, source: "manual" },
          ],
        },
      },
    );
    expect(apiBulk.ok()).toBeTruthy();

    await page
      .getByRole("link", { name: "项目列表" })
      .or(page.getByRole("button", { name: /打开/ }))
      .first()
      .click();
    // 不同实现可能在卡片上点"打开"
    if (await page.locator(`text=${freshProject.name}`).count()) {
      await page.click(`text=${freshProject.name} >> .. >> text=打开`);
    }

    await expect(page.getByText(/FP 编辑.*#/)).toBeVisible();
    await expect(page.locator("table tbody tr")).toHaveCount(5);

    // 3. 跳到结果页
    await page.getByRole("button", { name: "计算 → 结果页" }).click();

    await expect(page.getByText(/评估结果.*正向/)).toBeVisible();

    // 4. 三档卡片渲染
    const cards = page.locator("[data-band]");
    await expect(cards).toHaveCount(3);
    await expect(page.locator("[data-band='P50'][data-recommended='true']")).toBeVisible();
    await expect(page.locator("[data-band='P50']")).toContainText(/万元/);

    // 5. 下载 Excel
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /下载 Excel 报告/ }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain(".xlsx");
  });
});
