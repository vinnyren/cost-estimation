import { test, expect } from "./fixtures";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

/**
 * v2.1 C6 — StaleBanner 在 SPA 流程中在用户改 override 后回到结果页时显示。
 *
 * StaleBanner 由 useResultsStore.isStale 驱动：lastComputedAt < paramsChangedAt → 显示。
 * 而 ParamManager.patchOverride 会同步调用 markParamsChanged()。
 *
 * 关键约束：pinia 状态只在同一 SPA session 内保留，page.goto 会重置。
 * 因此测试用一次 page.goto 进入 ResultView，再通过 history.pushState + popstate 切到
 * ParamManager，编辑 override，再 history.back() 触发 popstate 回到 ResultView。
 *
 * 验证点：返回 ResultView 时 isStale=true → banner 立即可见（在 loadAndCompute 完成前
 * 的窗口期内）。banner 文本 "参数已变，结果可能过期" 与 StaleBanner.vue 一致。
 */
test("改 override 后结果页显示 stale banner", async ({ page, baseURL, request }) => {
  const create = await request.post(`${baseURL}/api/projects`, {
    headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
    data: {
      name: `e2e-stale-${Date.now()}`,
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
    // 加一个 FP（forward 需要 ≥1 个 FP，否则 NO_FUNCTION_POINTS 守护拒绝计算）
    await request.post(`${baseURL}/api/projects/${pid}/functions`, {
      headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
      data: {
        name: "fp1",
        category: "EI",
        complexity: "low",
        ufp: 3,
        us: 3,
        source: "manual",
      },
    });

    // 1) 进 ResultView — onMounted 跑 forward → lastComputedAt 置位
    await page.goto(`${baseURL}/projects/${pid}/result?t=${TOKEN}`);
    // 等 forward 完成（结果卡片出现）
    await expect(page.locator("h1#title")).toBeVisible();
    await page.waitForLoadState("networkidle").catch(() => {});

    // 2) SPA 内导航到 ParamManager — 用 history.pushState + popstate 保留 pinia state
    await page.evaluate((url) => {
      window.history.pushState({}, "", url);
      window.dispatchEvent(new PopStateEvent("popstate", { state: {} }));
    }, `/projects/${pid}/parameters?t=${TOKEN}`);
    await page.waitForLoadState("networkidle").catch(() => {});

    // 改"北京（开发）"OverrideField → patchOverride → markParamsChanged
    const bjDev = page.locator('input[aria-label="北京（开发）"]');
    await expect(bjDev).toBeVisible({ timeout: 5000 });
    await bjDev.fill("1234");
    await bjDev.dispatchEvent("input");
    // 等 patchOverride 返回 + markParamsChanged 同步执行
    await page.waitForTimeout(500);

    // 3) SPA 内返回 ResultView — pinia.isStale 此刻应为 true
    await page.evaluate((url) => {
      window.history.pushState({}, "", url);
      window.dispatchEvent(new PopStateEvent("popstate", { state: {} }));
    }, `/projects/${pid}/result?t=${TOKEN}`);

    // banner 在 loadAndCompute 完成前可见 — 用 waitFor 抓首次渲染的窗口
    const banner = page.locator("text=参数已变，结果可能过期");
    await expect(banner.first()).toBeVisible({ timeout: 3000 });
  } finally {
    await request
      .delete(`${baseURL}/api/projects/${pid}`, {
        headers: { "X-Auth-Token": TOKEN },
      })
      .catch(() => {});
  }
});
