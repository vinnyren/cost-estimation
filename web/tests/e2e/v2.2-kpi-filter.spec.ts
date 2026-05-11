import { test, expect, type Page } from "@playwright/test";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

const MOCK_STATS = {
  counts: { total: 5, draft: 2, in_progress: 2, archived: 1, delivered: 0 },
  monthly_count: 3,
  monthly_p50_sum: 1_200_000,
  monthly_growth_pct: 12.5,
};

/** Intercept /api/projects/stats before navigation to guarantee KPI row renders. */
async function mockStats(page: Page) {
  await page.route(/\/api\/projects\/stats/, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_STATS),
    })
  );
}

test.describe("v2.2 ProjectList KPI + Filter", () => {
  test("KPI cards render with counts from /api/projects/stats", async ({
    page,
    baseURL,
  }) => {
    await mockStats(page);
    await page.goto(`${baseURL}/?t=${TOKEN}`);
    await expect(page.locator(".kpi-row")).toBeVisible();
    // 4 status buttons + 1 summary div = 5 .kpi-card elements
    await expect(page.locator(".kpi-card")).toHaveCount(5);
    await expect(page.locator(".kpi-summary")).toContainText("本月总造价");
  });

  test("clicking 草稿 KPI card filters table", async ({ page, baseURL }) => {
    await mockStats(page);
    await page.goto(`${baseURL}/?t=${TOKEN}`);
    // Wait for KPI row to appear (stats loaded via mock)
    await expect(page.locator(".kpi-row")).toBeVisible();
    await page.locator(".kpi-card", { hasText: "草稿" }).click();
    await expect(
      page.locator(".kpi-card.active", { hasText: "草稿" })
    ).toBeVisible();
  });

  test("filter bar switches between table and card view", async ({
    page,
    baseURL,
    request,
  }) => {
    // Ensure at least one project exists so card-grid renders (not EmptyState)
    const created = await request.post(`${baseURL}/api/projects`, {
      headers: { "X-Auth-Token": TOKEN },
      data: {
        name: `e2e-kpi-view-${Date.now()}`,
        project_type: "dev_only",
        mode: "forward",
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
      await mockStats(page);
      await page.goto(`${baseURL}/?t=${TOKEN}`);
      // Wait for KPI row to appear
      await expect(page.locator(".kpi-row")).toBeVisible();

      // Switch to card view via the second seg button
      const cardBtn = page.locator(".seg button").nth(1);
      await cardBtn.click();
      await expect(page.locator(".card-grid")).toBeVisible();
    } finally {
      // Teardown: delete the seed project
      await request.delete(`${baseURL}/api/projects/${id}`, {
        headers: { "X-Auth-Token": TOKEN },
      });
    }
  });
});
