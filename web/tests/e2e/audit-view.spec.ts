import { test, expect } from "./fixtures";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

test("AuditView — 项目操作后审计页有记录", async ({ page, baseURL, request }) => {
  const create = await request.post(`${baseURL}/api/projects`, {
    headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
    data: {
      name: `e2e-audit-${Date.now()}`,
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
    // 改名（PATCH） — 制造一条 project.update 审计
    await request.patch(`${baseURL}/api/projects/${pid}`, {
      headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
      data: { name: "renamed-by-e2e" },
    });

    await page.goto(`${baseURL}/projects/${pid}/audit?t=${TOKEN}`);
    await page.waitForLoadState("networkidle").catch(() => {});

    // 验至少 2 行 audit（create + update）
    const rows = page.locator('[data-testid="audit-row"]');
    await expect(rows).toHaveCount(2);
    // 验内容包含中文标签（来自 AuditView.vue ACTION_LABELS）
    await expect(page.locator("text=创建项目")).toBeVisible();
    await expect(page.locator("text=修改项目")).toBeVisible();
  } finally {
    await request
      .delete(`${baseURL}/api/projects/${pid}`, {
        headers: { "X-Auth-Token": TOKEN },
      })
      .catch(() => {});
  }
});
