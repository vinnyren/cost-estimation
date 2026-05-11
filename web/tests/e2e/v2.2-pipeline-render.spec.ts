import { test, expect, request } from "@playwright/test";

const BASE_URL = "http://127.0.0.1:8788";
const AUTH_TOKEN = "e2e-token";

async function createForwardProjectWithFps(): Promise<string> {
  const ctx = await request.newContext({
    baseURL: BASE_URL,
    extraHTTPHeaders: {
      "X-Auth-Token": AUTH_TOKEN,
      "content-type": "application/json",
      Origin: BASE_URL,
    },
  });
  const r = await ctx.post("/api/projects", {
    data: {
      name: `Pipeline E2E ${Date.now()}`,
      project_type: "dev_only",
      phase: "bidding",
      city: "北京",
      industry: "电子政务",
      mode: "forward",
      basis_data_ver: "CSBMK-202510",
      other_cost: 25000,
    },
  });
  expect(r.status()).toBe(201);
  const body = await r.json();
  const pid = body.data?.id ?? body.id;
  await ctx.post(`/api/projects/${pid}/functions/bulk`, {
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
          l1_module: "档案",
          category: "ILF",
          complexity: "average",
          ufp: 10,
          us: 10,
          reuse_level: "low",
          modify_type: "new",
          source: "manual",
        },
      ],
    },
  });
  return pid;
}

test("ResultView forward 显示 Pipeline 9 步", async ({ page }) => {
  const pid = await createForwardProjectWithFps();
  await page.goto(`/projects/${pid}/result`);
  await page.waitForLoadState("networkidle");
  const cells = page.locator(".pipeline-cell");
  await expect(cells).toHaveCount(9, { timeout: 10000 });
  await expect(page.locator(".pipeline-cell.final")).toContainText("元");
});
