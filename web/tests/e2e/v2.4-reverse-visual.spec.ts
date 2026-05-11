import { test, expect, request } from "@playwright/test";

const BASE_URL = "http://127.0.0.1:8788";
const AUTH_TOKEN = "e2e-token";

async function createReverseProject(): Promise<string> {
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
      name: `Reverse Visual E2E ${Date.now()}`,
      project_type: "dev_only",
      phase: "bidding",
      city: "北京",
      industry: "电子政务",
      mode: "reverse",
      basis_data_ver: "CSBMK-202510",
      target_cost: 1500000,
      other_cost: 60000,
    },
  });
  expect(r.status()).toBe(201);
  const body = await r.json();
  return body.data?.id ?? body.id;
}

test("v2.4 reverse: 4 列 grid + ResultTrio + hero-bg + header download", async ({ page }) => {
  const pid = await createReverseProject();
  await page.goto(`/projects/${pid}/result`);
  await page.waitForLoadState("networkidle");

  // hero-bg 应用到 .page
  await expect(page.locator(".page.hero-bg")).toBeVisible();

  // 反算输入卡片 4 列
  await expect(page.locator("label.field-label", { hasText: "目标总造价" })).toBeVisible();
  await expect(page.locator("label.field-label", { hasText: "其他费用" })).toBeVisible();
  await expect(page.locator("label.field-label", { hasText: "可用预算" })).toBeVisible();
  await expect(page.locator("label.field-label", { hasText: "α 开发占比" })).toBeVisible();

  // 可用预算 disabled
  const availableInput = page.locator("input").nth(2);
  await expect(availableInput).toBeDisabled();

  // 点反算
  await page.locator(".btn-primary", { hasText: "反算" }).click();
  await page.waitForLoadState("networkidle");

  // ResultTrio 3 卡片渲染
  await expect(page.locator(".result-trio .result-card")).toHaveCount(3);
  await expect(page.locator(".result-card.recommended")).toBeVisible();

  // FP 单位
  await expect(page.locator(".result-card-amt").first()).toContainText("FP");

  // 卡片 label 文案
  await expect(page.locator(".result-card-name").nth(0)).toContainText("乐观");
  await expect(page.locator(".result-card-name").nth(1)).toContainText("中位");
  await expect(page.locator(".result-card-name").nth(2)).toContainText("保守");

  // page-header 含 reverse 下载按钮
  await expect(page.locator(".page-header .btn-primary", { hasText: "下载" })).toBeVisible();

  // AllocatorPanel 仍在
  await expect(page.locator(".allocator-panel")).toBeVisible();
});
