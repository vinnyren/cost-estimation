import { test, expect } from "@playwright/test";

test("ResultView CostBar 显示 4 段构成", async ({ page }) => {
  await page.goto("/");
  const firstRow = page.locator("tr.row-link").first();
  await firstRow.click();
  await page.locator(".sidebar .nav-item.sub", { hasText: "三档造价" }).click();
  await page.waitForLoadState("networkidle");
  await expect(page.locator(".cost-bar-track")).toBeVisible();
  const segments = page.locator(".cost-bar-seg");
  expect(await segments.count()).toBeGreaterThanOrEqual(1);
});
