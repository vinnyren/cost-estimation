import { test, expect } from "./fixtures";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

test("bulk_write 后 fp_snapshot 自动产生", async ({ request, baseURL }) => {
  const create = await request.post(`${baseURL}/api/projects`, {
    headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
    data: {
      name: `e2e-bulk-${Date.now()}`,
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
    // 先单独 POST 一个 FP
    await request.post(`${baseURL}/api/projects/${pid}/functions`, {
      headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
      data: { name: "manual-fp", category: "EI", complexity: "low", ufp: 3, us: 3, source: "manual" },
    });

    // 然后 bulk_write replace=true — 应触发 pre_bulk_replace snapshot
    await request.post(`${baseURL}/api/projects/${pid}/functions/bulk`, {
      headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
      data: {
        items: [
          { name: "bulk-fp", category: "EQ", complexity: "average", ufp: 4, us: 4, source: "manual" },
        ],
        replace: true,
      },
    });

    // 验 snapshot 列表至少 1 行 pre_bulk_replace
    const snaps = await request.get(`${baseURL}/api/projects/${pid}/functions/snapshots`, {
      headers: { "X-Auth-Token": TOKEN },
    });
    const rows = (await snaps.json()).data;
    const preBulk = rows.find((s: { reason: string }) => s.reason === "pre_bulk_replace");
    expect(preBulk).toBeDefined();
  } finally {
    await request
      .delete(`${baseURL}/api/projects/${pid}`, {
        headers: { "X-Auth-Token": TOKEN },
      })
      .catch(() => {});
  }
});
