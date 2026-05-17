import { test, expect, request } from "@playwright/test";

const BASE_URL = "http://127.0.0.1:8788";
const AUTH_TOKEN = "e2e-token";

async function createProjectWithUpload(): Promise<string> {
  const ctx = await request.newContext({
    baseURL: BASE_URL,
    extraHTTPHeaders: {
      "X-Auth-Token": AUTH_TOKEN,
      Origin: BASE_URL,
    },
  });
  // 创建项目
  const r = await ctx.post("/api/projects", {
    headers: { "content-type": "application/json" },
    data: {
      name: `Upload E2E ${Date.now()}`,
      project_type: "dev_only",
      phase: "bidding",
      city: "北京",
      industry: "电子政务",
      mode: "forward",
      basis_data_ver: "CSBMK-202510",
    },
  });
  expect(r.status()).toBe(201);
  const body = await r.json();
  const pid = body.data?.id ?? body.id;

  // 上传 dummy 文件
  const buf = Buffer.from("hello upload e2e test content");
  const up = await ctx.post(`/api/projects/${pid}/uploads`, {
    multipart: {
      file: { name: "test.txt", mimeType: "text/plain", buffer: buf },
    },
  });
  expect(up.status()).toBe(201);
  return pid;
}

test("v2.5 已上传文件主页面区块 + 删除", async ({ page }) => {
  const pid = await createProjectWithUpload();
  await page.goto(`/projects/${pid}/functions`);
  await page.waitForLoadState("networkidle");

  // 上传文件区块直接在主页面渲染（无需点按钮）
  const section = page.locator(".upload-section");
  await expect(section).toBeVisible();
  await expect(section).toContainText("已上传文件");

  // 表格有 1 行，含文件名
  await expect(section.locator("table tbody tr")).toHaveCount(1);
  await expect(section).toContainText("test.txt");

  // 删除 — auto accept confirm
  page.once("dialog", (d) => d.accept());
  await section.locator("button", { hasText: "删除" }).click();
  await page.waitForLoadState("networkidle");

  // 0 个文件后整块不再渲染
  await expect(page.locator(".upload-section")).toHaveCount(0);
});
