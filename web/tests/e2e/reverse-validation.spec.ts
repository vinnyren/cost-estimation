// web/tests/e2e/reverse-validation.spec.ts
import { test, expect } from "./fixtures";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

test("Wizard reverse 模式 target_total=0 → 下一步 disabled", async ({ page, baseURL }) => {
  await page.goto(`${baseURL}/projects/new?t=${TOKEN}`);
  await page.waitForLoadState("networkidle").catch(() => {});

  await page.locator('input[name="name"]').fill("validation-test");
  await page.locator('[data-test="wizard-next"]').click(); // → step 2
  await page.waitForTimeout(100);
  await page.locator('[data-test="wizard-next"]').click(); // → step 3
  await page.waitForTimeout(100);
  await page.locator('[data-test="wizard-next"]').click(); // → step 4
  await page.waitForTimeout(100);

  // Step 4: 选 reverse
  await page.locator('input[value="reverse"]').click();
  await page.waitForTimeout(100);

  // target_total 默认 0 — next 应 disabled
  const nextBtn = page.locator('[data-test="wizard-next"]');
  await expect(nextBtn).toBeDisabled();

  // 填正数 → enabled
  await page.locator('input[name="target_total"]').fill("1000");
  await page.waitForTimeout(50);
  await expect(nextBtn).toBeEnabled();
});
