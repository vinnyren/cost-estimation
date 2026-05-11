// web/tests/e2e/wizard-dev-and-ops.spec.ts
import { test, expect } from "./fixtures";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

test("Wizard dev_and_ops — α 滑块 + ops 因子可见", async ({ page, baseURL, request }) => {
  await page.goto(`${baseURL}/projects/new?t=${TOKEN}`);
  await page.waitForLoadState("networkidle").catch(() => {});

  const name = `e2e-d+o-${Date.now()}`;
  await page.locator('input[name="name"]').fill(name);
  await page.locator('[data-test="wizard-next"]').click();
  await page.waitForTimeout(150);

  // Step 2: 选 dev_and_ops
  await page.locator('input[value="dev_and_ops"]').click();
  // 验 α 滑块出现
  await expect(page.locator('input[type="range"]')).toBeVisible();
  // 验 include_ops 自动选中
  await expect(page.locator('input[type="checkbox"]:checked').first()).toBeVisible();

  // 拉滑块到 0.85
  await page.locator('input[type="range"]').fill("0.85");
  await page.locator('[data-test="wizard-next"]').click(); // step 3
  await page.waitForTimeout(100);
  await page.locator('[data-test="wizard-next"]').click(); // step 4
  await page.waitForTimeout(100);
  await page.locator('[data-test="wizard-next"]').click(); // step 5
  await page.waitForTimeout(100);
  await page.locator('[data-test="wizard-next"]').click(); // step 6 (ops factors)
  await page.waitForTimeout(150);

  // step 6 应该有 ops factor dropdowns（多个 select）
  const selectCount = await page.locator('select').count();
  expect(selectCount).toBeGreaterThan(0);

  let createdPid: string | null = null;
  try {
    await page.locator('[data-test="wizard-next"]').click(); // step 7
    await page.waitForTimeout(100);
    await page.locator('button:has-text("创建项目")').click();
    await page.waitForTimeout(800);
    const url = page.url();
    createdPid = url.match(/projects\/([^/]+)/)?.[1] ?? null;
    expect(createdPid).toBeTruthy();
  } finally {
    if (createdPid) {
      await request.delete(`${baseURL}/api/projects/${createdPid}`, {
        headers: { "X-Auth-Token": TOKEN },
      }).catch(() => {});
    }
  }
});
