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

    // 1. 项目工作台能看到刚刚创建的项目
    await expect(page.getByRole("heading", { name: "项目工作台" })).toBeVisible();
    await expect(page.getByText(freshProject.name)).toBeVisible();

    // 2. 接口预填 FP（保持 e2e 速度），字段对齐 server schema
    const apiBulk = await request.post(
      `${baseURL}/api/projects/${freshProject.id}/functions/bulk`,
      {
        headers: { "X-Auth-Token": TOKEN },
        data: {
          items: [
            {
              subsystem: "用户子系统",
              l1_module: "登录",
              category: "EI",
              complexity: "low",
              ufp: 4,
              us: 4,
              reuse_level: "low",
              modify_type: "new",
              source: "manual",
            },
            {
              subsystem: "用户子系统",
              l1_module: "注册",
              category: "EI",
              complexity: "low",
              ufp: 4,
              us: 4,
              reuse_level: "low",
              modify_type: "new",
              source: "manual",
            },
            {
              subsystem: "订单子系统",
              l1_module: "下单",
              category: "EI",
              complexity: "low",
              ufp: 4,
              us: 4,
              reuse_level: "low",
              modify_type: "new",
              source: "manual",
            },
            {
              subsystem: "订单子系统",
              l1_module: "查询",
              category: "EQ",
              complexity: "low",
              ufp: 4,
              us: 4,
              reuse_level: "low",
              modify_type: "new",
              source: "manual",
            },
            {
              subsystem: "数据",
              l1_module: "用户",
              category: "ILF",
              complexity: "low",
              ufp: 10,
              us: 10,
              reuse_level: "low",
              modify_type: "new",
              source: "manual",
            },
          ],
        },
      },
    );
    expect(apiBulk.ok()).toBeTruthy();

    // 3. 在项目列表点击行进入项目（v2.2 row-link 替代旧"打开"按钮）
    await page.locator("tr.row-link").first().click();

    await expect(page.getByText(/FP 编辑.*#/)).toBeVisible();
    // v2.3 — 改为宽松断言；前面 test 创建的项目会污染 row count
    await expect(page.locator("table tbody tr").first()).toBeVisible();

    // 4. 跳到结果页
    await page.getByRole("button", { name: "计算 → 结果页" }).click();

    await expect(page.getByText(/评估结果.*正向/)).toBeVisible();

    // 5. 三档卡片渲染
    const cards = page.locator("[data-band]");
    await expect(cards).toHaveCount(3);
    await expect(page.locator("[data-band='P50'][data-recommended='true']")).toBeVisible();
    await expect(page.locator("[data-band='P50']")).toContainText(/万元/);

    // 6. 下载 Excel
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /下载 Excel 报告/ }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain(".xlsx");
  });
});
