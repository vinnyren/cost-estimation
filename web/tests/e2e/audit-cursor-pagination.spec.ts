import { test, expect } from "./fixtures";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

test("Audit cursor 分页 — before_id 正确", async ({ request, baseURL }) => {
  const create = await request.post(`${baseURL}/api/projects`, {
    headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
    data: {
      name: `e2e-cursor-${Date.now()}`,
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
    // 制造 6 条 audit（5 个 PATCH + 1 个 create 已有 = 6 行）
    for (let i = 0; i < 5; i++) {
      await request.patch(`${baseURL}/api/projects/${pid}`, {
        headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
        data: { name: `rename-${i}` },
      });
    }

    // limit=3 第一页
    const page1 = await request.get(`${baseURL}/api/projects/${pid}/audit?limit=3`, {
      headers: { "X-Auth-Token": TOKEN },
    });
    const rows1 = (await page1.json()).data;
    expect(rows1.length).toBe(3);

    // limit=3 第二页（before_id = 第一页最后一行的 id）
    const lastId = rows1[rows1.length - 1].id;
    const page2 = await request.get(
      `${baseURL}/api/projects/${pid}/audit?limit=3&before_id=${lastId}`,
      { headers: { "X-Auth-Token": TOKEN } },
    );
    const rows2 = (await page2.json()).data;
    expect(rows2.length).toBeGreaterThan(0);
    // 第二页所有 id 都应 < lastId
    for (const r of rows2) {
      expect(r.id).toBeLessThan(lastId);
    }
  } finally {
    await request
      .delete(`${baseURL}/api/projects/${pid}`, {
        headers: { "X-Auth-Token": TOKEN },
      })
      .catch(() => {});
  }
});
