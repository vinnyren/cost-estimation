import { test, expect } from "./fixtures";

/**
 * T19 — Wizard 7 步 E2E。
 *
 * 覆盖 ProjectWizard.vue（T13-T18 后的 v2.0 实装）：
 *   1) 基础信息 → 2) 项目类型 → 3) 阶段 → 4) 正/反向
 *   5) 开发因子 → 6) 运维因子 → 7) 确认 → POST /api/projects → 跳到 FP 页
 *
 * Selector 优先级：data-testid > name= > role+name > 文本。
 * 任何 DOM 变动只需调整 selector，无需重写测试逻辑。
 *
 * 注意：FP 编辑路由是 /projects/:id/functions（router/index.ts）。
 */
test.describe("Wizard v2.0 7 步流程", () => {
  test("完整向导创建 dev_only forward 项目 → 跳转 FP 编辑页", async ({
    page,
    baseURL,
    request,
  }) => {
    const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";
    const projectName = `e2e-wizard-${Date.now()}`;
    let createdId: string | null = null;

    try {
      // 0. 用 URL token 让 SPA 把 token 写入 sessionStorage（与 forward.spec 一致）
      await page.goto(`${baseURL}/projects/new?t=${TOKEN}`);
      await expect(page.getByRole("heading", { name: "新建项目" })).toBeVisible();

      // Step 1: 基础信息（项目名必填）
      await page.locator('input[name="name"]').fill(projectName);
      await page.locator('input[name="client"]').fill("测试客户");
      await page.locator('input[name="evaluator"]').fill("测试评估方");
      await page.locator('[data-test="wizard-next"]').click();

      // Step 2: 项目类型 — dev_only（默认即如此，显式点击以验证 radio 渲染）
      await page.locator('input[name="project_type"][value="dev_only"]').check();
      await page.locator('[data-test="wizard-next"]').click();

      // Step 3: 阶段 — bidding（招标），通过 PhaseCfPreview 的 data-testid
      await page
        .locator('[data-testid="phase-card-bidding"] input[type="radio"]')
        .check();
      await page.locator('[data-test="wizard-next"]').click();

      // Step 4: 正/反向 — forward（默认）
      await page.locator('input[name="mode"][value="forward"]').check();
      await page.locator('[data-test="wizard-next"]').click();

      // Step 5: 开发因子（全部用默认空值 → ×1.00 链）
      await expect(
        page.locator('[data-testid="dev-factor-preview"]'),
      ).toContainText("1.00");
      await page.locator('[data-test="wizard-next"]').click();

      // Step 6: 运维因子 — dev_only 时跳过提示
      await expect(page.locator('[data-testid="ops-skip"]')).toBeVisible();
      await page.locator('[data-test="wizard-next"]').click();

      // Step 7: 确认 — 校验项目名展示后提交
      const summary = page.locator('[data-testid="confirm-summary"]');
      await expect(summary).toBeVisible();
      await expect(summary.locator('[data-field="name"]')).toHaveText(
        projectName,
      );
      await page.getByRole("button", { name: "创建项目" }).click();

      // 跳到 FP 编辑页（router name=fp-editor → /projects/:id/functions）
      await page.waitForURL(/\/projects\/[^/]+\/functions/, { timeout: 15_000 });
      const match = page.url().match(/\/projects\/([^/]+)\/functions/);
      expect(match).toBeTruthy();
      createdId = match![1];

      // 落地页确认是 FP Editor
      await expect(page.getByText(/FP 编辑.*#/)).toBeVisible();
    } finally {
      // teardown — 走 API 删除避开 confirm dialog
      if (createdId) {
        await request.delete(`${baseURL}/api/projects/${createdId}`, {
          headers: { "X-Auth-Token": TOKEN },
        });
      }
    }
  });
});
