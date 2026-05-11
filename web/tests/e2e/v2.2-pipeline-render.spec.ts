import { test, expect } from "@playwright/test";

test("ResultView forward 显示 Pipeline 9 步", async ({ page }) => {
  await page.goto("/");
  const firstRow = page.locator("tr.row-link").first();
  await firstRow.click();
  // 通过 sidebar 进 ResultView
  await page.locator(".sidebar .nav-item.sub", { hasText: "三档造价" }).click();
  await page.waitForLoadState("networkidle");
  const cells = page.locator(".pipeline-cell");
  await expect(cells).toHaveCount(9);
  await expect(page.locator(".pipeline-cell.final")).toContainText("元");
});
