/**
 * T9 — v2.2 Design Shell E2E
 *
 * 验证:
 *   1) Sidebar 渲染 5 个主导航项，项目子导航在非项目路由下不显示
 *   2) ⌘K / Ctrl+K 打开 CommandPalette，Esc 关闭
 *   3) Breadcrumbs 随路由更新
 *
 * 注意: 使用 ?t=TOKEN URL param 注入 auth（与其他 e2e 一致）。
 */
import { test, expect } from "@playwright/test";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

test.describe("v2.2 Design Shell", () => {
  test("sidebar shows 5 main nav items + project sub-nav appears on project route", async ({
    page,
    baseURL,
    request,
  }) => {
    // Inject token via URL param (same pattern as other e2e specs)
    await page.goto(`${baseURL}/?t=${TOKEN}`);

    // Sidebar should be visible (first .sidebar = main nav shell)
    const sidebar = page.locator(".sidebar").first();
    await expect(sidebar).toBeVisible();

    // 5 main nav items (项目工作台, 全局参数库, 模板与场景, 报告中心, 审计日志)
    const navItems = sidebar.locator(".nav-item");
    await expect(navItems).toHaveCount(5);

    // First item = 项目工作台
    await expect(navItems.first()).toContainText("项目工作台");

    // 模板与场景 is disabled
    const disabledItem = sidebar.locator(".nav-item.disabled");
    await expect(disabledItem).toContainText("模板与场景");

    // Project sub-nav should NOT appear on the list page (no :id in route)
    const subItems = sidebar.locator(".nav-item.sub");
    await expect(subItems).toHaveCount(0);

    // Navigate to a project if one exists; otherwise skip sub-nav assertions.
    // T14 redesign replaced "打开" button with row-link click navigation.
    const firstRow = page.locator("tr.row-link").first();
    if (await firstRow.count() > 0) {
      await firstRow.click();
      // After navigating to a project page, sub-nav section should show 4 items
      await expect(sidebar.locator(".nav-item.sub")).toHaveCount(4);
      await expect(sidebar).toContainText("FP 编辑");
    }
  });

  test("Cmd+K opens command palette", async ({ page, baseURL }) => {
    await page.goto(`${baseURL}/?t=${TOKEN}`);

    const meta = process.platform === "darwin" ? "Meta" : "Control";
    await page.keyboard.press(`${meta}+KeyK`);

    const palette = page.locator(".palette");
    await expect(palette).toBeVisible();

    // Escape closes the palette
    await page.keyboard.press("Escape");
    await expect(palette).not.toBeVisible();
  });

  test("breadcrumb updates with route", async ({ page, baseURL }) => {
    await page.goto(`${baseURL}/projects/new?t=${TOKEN}`);

    // Breadcrumb nav (.crumbs) should show both segments
    const crumbs = page.locator(".crumbs");
    await expect(crumbs).toContainText("项目工作台");
    await expect(crumbs).toContainText("新建项目");
  });
});
