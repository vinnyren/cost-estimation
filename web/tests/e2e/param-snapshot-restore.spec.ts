import { test, expect } from "./fixtures";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

test("Snapshot 创建 + restore 恢复全局参数", async ({ request, baseURL }) => {
  // 1. 改 hours_per_pm 让它偏离默认
  await request.patch(`${baseURL}/api/params/global`, {
    headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
    data: { key: "hours_per_pm", value: 200 },
  });

  // 2. 拍 snapshot
  const create = await request.post(`${baseURL}/api/params/snapshots`, {
    headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
    data: { scope: "global", label: "before-second-edit" },
  });
  expect(create.status()).toBe(201);
  const snapId = (await create.json()).data.id;

  // 3. 再改 hours_per_pm → 300
  await request.patch(`${baseURL}/api/params/global`, {
    headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
    data: { key: "hours_per_pm", value: 300 },
  });

  try {
    // 4. Restore snapshot
    const restore = await request.post(
      `${baseURL}/api/params/snapshots/${snapId}/restore`,
      { headers: { "X-Auth-Token": TOKEN } },
    );
    expect(restore.status()).toBe(200);

    // 5. 验 hours_per_pm 恢复到 200
    const eff = await request.get(`${baseURL}/api/params/effective`, {
      headers: { "X-Auth-Token": TOKEN },
    });
    const data = (await eff.json()).data;
    expect(data.hours_per_pm).toBe(200);
  } finally {
    // 6. 清理 — 删 snapshot + 重置 hours_per_pm（避免污染后续 test）
    await request
      .delete(`${baseURL}/api/params/snapshots/${snapId}`, {
        headers: { "X-Auth-Token": TOKEN },
      })
      .catch(() => {});
    // 重置回 CSBMK 默认（174 per v2.0 csbmk_202510.json）
    await request
      .patch(`${baseURL}/api/params/global`, {
        headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
        data: { key: "hours_per_pm", value: 174 },
      })
      .catch(() => {});
  }
});
