import { test, expect } from "./fixtures";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

test("AllocatorPanel: 新增/删除 drafts → 生成分摊 → 看到一致性 banner", async ({
  page,
  request,
  baseURL,
}) => {
  // 建反向项目
  const create = await request.post(`${baseURL}/api/projects`, {
    headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
    data: {
      name: `Allocator E2E ${Date.now()}`,
      project_type: "dev_only",
      phase: "bidding",
      city: "北京",
      industry: "电子政务",
      mode: "reverse",
      basis_data_ver: "CSBMK®-202510",
      target_cost: 1500000,
      other_cost: 0,
    },
  });
  expect(create.status()).toBe(201);
  const pid = (await create.json()).data.id;

  try {
    await page.goto(`/projects/${pid}/result`);
    await page.waitForLoadState("networkidle");

    // 先触发反算（输入目标金额）
    const targetInput = page.locator("input[type='number']").first();
    await targetInput.fill("1500000");
    await page.getByRole("button", { name: "反算" }).click();
    await page.waitForLoadState("networkidle");

    // reverse 路径展示 AllocatorPanel（可能在折叠区域，先滚动进视口）
    const panel = page.locator(".allocator-panel");
    await expect(panel).toBeAttached({ timeout: 10000 });
    await panel.scrollIntoViewIfNeeded();
    await expect(panel).toBeVisible({ timeout: 5000 });

    // 默认 2 行 drafts（前端、后端）
    await expect(panel.locator(".allocator-drafts tbody tr")).toHaveCount(2);

    // 新增 1 行 = 3 行
    await panel.getByRole("button", { name: "+ 新增模块" }).click();
    await expect(panel.locator(".allocator-drafts tbody tr")).toHaveCount(3);

    // 删除最后一行 = 2 行
    const deleteButtons = panel.locator("button[aria-label='删除']");
    await deleteButtons.last().click();
    await expect(panel.locator(".allocator-drafts tbody tr")).toHaveCount(2);

    // 生成分摊
    await panel.getByRole("button", { name: /生成分摊/ }).click();

    // 一致性 banner 出现
    const banner = panel.locator(".banner-green");
    await expect(banner).toBeVisible({ timeout: 10000 });
    await expect(banner).toContainText("误差");
    await expect(banner).toContainText("%");
  } finally {
    await request
      .delete(`${baseURL}/api/projects/${pid}`, {
        headers: { "X-Auth-Token": TOKEN },
      })
      .catch(() => {});
  }
});
