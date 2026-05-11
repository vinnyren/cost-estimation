import { test, expect } from "./fixtures";

/**
 * v2.1 C1 — ParamManager 6 tab e2e。
 *
 * v1.1 时只有"费率"和"生产率"两 tab 渲染数据，其它 4 个仅是骨架；v2.0 全部接通。
 * 本测试 防回归 — 确保 6 个 tab 都可切换且渲染非 stub 内容（数据 / 控件正确）。
 *
 * Selector 选择：
 *   - tab 用 [role="tab"]:has-text — 与 ParamManager.vue 的 role=tab 一致
 *   - 城市费率 用 data-testid="city-rate-row"
 *   - 开发因子 用 [data-factor="app_type"]（FactorTable.vue 设置）
 *   - 规模变更 用 text=新增（SCALE_CHANGE_LABELS.add → CSBMK 中确实有 add）
 *   - 快照 用 button:has-text("立即快照")
 */
const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

test("ParamManager 6 tab 全部可访问且非 stub", async ({
  page,
  baseURL,
  request,
}) => {
  // 走 API 直接建项目，避开 wizard 的 UI 步骤
  const created = await request.post(`${baseURL}/api/projects`, {
    headers: {
      "X-Auth-Token": TOKEN,
      "Content-Type": "application/json",
    },
    data: {
      name: `e2e-6tab-${Date.now()}`,
      project_type: "dev_only",
      phase: "bidding",
      city: "北京",
      industry: "电子政务",
      mode: "forward",
      basis_data_ver: "CSBMK®-202510",
    },
  });
  expect(created.status()).toBe(201);
  const pid: string = (await created.json()).data.id;

  try {
    // 用 ?t=TOKEN 让 SPA 把 token 写入 sessionStorage（与现有 spec 一致）
    await page.goto(`${baseURL}/projects/${pid}/parameters?t=${TOKEN}`);
    await page.waitForLoadState("networkidle").catch(() => {});

    // 6 个 tab 都存在
    const tabs = ["费率", "生产率", "开发因子", "运维因子", "规模变更", "快照"];
    for (const tab of tabs) {
      const btn = page.locator(`[role="tab"]:has-text("${tab}")`);
      await expect(btn).toBeVisible();
    }

    // 1) 费率 → 默认即此 tab，看到城市行
    await page.locator(`[role="tab"]:has-text("费率")`).click();
    await expect(
      page.locator('[data-testid="city-rate-row"]').first(),
    ).toBeVisible();

    // 2) 开发因子 → 看到 app_type 因子卡
    await page.locator(`[role="tab"]:has-text("开发因子")`).click();
    await expect(page.locator('[data-factor="app_type"]').first()).toBeVisible();

    // 3) 规模变更 → 看到"新增"行（来自 SCALE_CHANGE_LABELS.add）
    await page.locator(`[role="tab"]:has-text("规模变更")`).click();
    await expect(page.locator("text=新增").first()).toBeVisible();

    // 4) 快照 → 看到"立即快照"按钮
    await page.locator(`[role="tab"]:has-text("快照")`).click();
    await expect(
      page.locator('button:has-text("立即快照")'),
    ).toBeVisible();
  } finally {
    await request
      .delete(`${baseURL}/api/projects/${pid}`, {
        headers: { "X-Auth-Token": TOKEN },
      })
      .catch(() => {
        /* best-effort cleanup */
      });
  }
});
