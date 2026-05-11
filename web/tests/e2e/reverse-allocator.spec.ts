import { test, expect } from "./fixtures";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

test("反向 + AI 模块分摊 — calc → allocator 渲染分摊结果", async ({ baseURL, request }) => {
  // 建反向项目
  const create = await request.post(`${baseURL}/api/projects`, {
    headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
    data: {
      name: `e2e-alloc-${Date.now()}`,
      project_type: "dev_only",
      phase: "budget",
      city: "上海",
      industry: "金融",
      mode: "reverse",
      target_cost: 5000000,
      basis_data_ver: "CSBMK®-202510",
    },
  });
  expect(create.status()).toBe(201);
  const pid = (await create.json()).data.id;

  try {
    // 反向 calc
    const reverse = await request.post(`${baseURL}/api/calc/reverse`, {
      headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
      data: { project_id: pid, target_total: 5000000 },
    });
    expect(reverse.status()).toBe(200);

    // 调 allocate（手动给 drafts JSON 模拟 AI 输出）
    const alloc = await request.post(`${baseURL}/api/calc/allocate`, {
      headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
      data: {
        project_id: pid,
        target_us: 100,
        drafts: [
          { name: "前端门户", weight: 1.0 },
          { name: "后台管理", weight: 2.0 },
        ],
        cf: 1.21,
      },
    });
    expect(alloc.status()).toBe(200);
    const allocData = await alloc.json();
    expect(allocData.data).toHaveLength(2);

    // 验返回值 us 字段（按 weight 比例分摊；2:1 比例下后台应该 ≈ 2 * 前端）
    const frontend = allocData.data.find(
      (x: { name: string; us: number }) => x.name === "前端门户",
    );
    const backend = allocData.data.find(
      (x: { name: string; us: number }) => x.name === "后台管理",
    );
    expect(frontend).toBeDefined();
    expect(backend).toBeDefined();
    expect(backend!.us).toBeGreaterThan(frontend!.us);
  } finally {
    await request
      .delete(`${baseURL}/api/projects/${pid}`, {
        headers: { "X-Auth-Token": TOKEN },
      })
      .catch(() => {});
  }
});
