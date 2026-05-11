import { test, expect } from "./fixtures";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

test("AuditView timeline renders dots for project events", async ({ page, baseURL, request }) => {
  // Create a project so we have at least one audit event (project.create)
  const create = await request.post(`${baseURL}/api/projects`, {
    headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
    data: {
      name: `e2e-audit-timeline-${Date.now()}`,
      project_type: "dev_only",
      phase: "bidding",
      city: "北京",
      industry: "电子政务",
      mode: "forward",
      basis_data_ver: "CSBMK®-202510",
    },
  });
  const pid = (await create.json()).data.id;

  try {
    await page.goto(`${baseURL}/projects/${pid}/audit?t=${TOKEN}`);
    await page.waitForLoadState("networkidle").catch(() => {});

    // The timeline component renders .tl-dot for each entry
    const dots = page.locator(".tl-dot");
    await expect(dots.first()).toBeVisible({ timeout: 5000 });

    // Should show the page title
    await expect(page.locator("h1")).toContainText("项目审计");

    // At minimum there is 1 dot (project.create event)
    const count = await dots.count();
    expect(count).toBeGreaterThanOrEqual(1);

    // Verify the create label is rendered by AuditTimeline
    await expect(page.locator("text=创建项目")).toBeVisible();
  } finally {
    await request
      .delete(`${baseURL}/api/projects/${pid}`, {
        headers: { "X-Auth-Token": TOKEN },
      })
      .catch(() => {});
  }
});

test("AuditView global mode shows v2.3 placeholder", async ({ page, baseURL }) => {
  await page.goto(`${baseURL}/audit?t=${TOKEN}`);
  await page.waitForLoadState("networkidle").catch(() => {});

  // Should show the global placeholder text
  await expect(page.locator("text=v2.3 上线")).toBeVisible({ timeout: 5000 });
  await expect(page.locator("h1")).toContainText("全局审计日志");
});
