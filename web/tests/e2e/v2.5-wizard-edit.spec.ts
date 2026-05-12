import { test, expect, request } from "@playwright/test";

const BASE_URL = "http://127.0.0.1:8788";
const AUTH_TOKEN = "e2e-token";

async function createProject(name: string): Promise<string> {
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
      name,
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
  return body.data?.id ?? body.id;
}

test("v2.5 edit wizard: 访问 /edit 显示 '编辑项目设定' 标题且预填 name", async ({
  page,
}) => {
  const name = `EditWizard E2E ${Date.now()}`;
  const pid = await createProject(name);

  await page.goto(`/projects/${pid}/edit`);
  await page.waitForLoadState("networkidle");

  // 标题切换为"编辑项目设定"
  await expect(page.getByText("编辑项目设定")).toBeVisible({ timeout: 10000 });

  // name 字段被预填 — step 1 中 <input name="name" type="text">
  const nameInput = page.locator('input[name="name"]');
  await expect(nameInput).toHaveValue(name, { timeout: 5000 });
});
