import { test, expect } from "./fixtures";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

test("项目复制 — API copy → 副本含 FP + diff_json", async ({ baseURL, request }) => {
  // 建项目 + 加 1 个 FP
  const create = await request.post(`${baseURL}/api/projects`, {
    headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
    data: {
      name: `e2e-copy-${Date.now()}`,
      project_type: "dev_only",
      phase: "bidding",
      city: "北京",
      industry: "电子政务",
      mode: "forward",
      basis_data_ver: "CSBMK®-202510",
    },
  });
  const pid = (await create.json()).data.id;
  await request.post(`${baseURL}/api/projects/${pid}/functions`, {
    headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
    data: { name: "fp1", category: "EI", complexity: "low", ufp: 3, us: 3, source: "manual" },
  });

  let copyPid: string | null = null;
  try {
    // 通过 API 直接 copy（UI 用 window.prompt 不易在 e2e 自动）
    const copy = await request.post(`${baseURL}/api/projects/${pid}/copy`, {
      headers: { "X-Auth-Token": TOKEN, "Content-Type": "application/json" },
      data: { name: "copy-by-e2e" },
    });
    expect(copy.status()).toBe(201);
    copyPid = (await copy.json()).data.id;
    expect(copyPid).not.toBe(pid);

    // 验副本含 1 个 FP
    const fps = await request.get(`${baseURL}/api/projects/${copyPid}/functions`, {
      headers: { "X-Auth-Token": TOKEN },
    });
    expect((await fps.json()).data.length).toBe(1);

    // 验副本 audit 含 copied_from
    const audit = await request.get(`${baseURL}/api/projects/${copyPid}/audit`, {
      headers: { "X-Auth-Token": TOKEN },
    });
    const rows = (await audit.json()).data;
    expect(rows.length).toBeGreaterThanOrEqual(1);
    const createEntry = rows.find((r: { action: string }) => r.action === "project.create");
    expect(createEntry).toBeDefined();
    expect(createEntry?.diff_json).toContain("copied_from");
  } finally {
    await request
      .delete(`${baseURL}/api/projects/${pid}`, {
        headers: { "X-Auth-Token": TOKEN },
      })
      .catch(() => {});
    if (copyPid) {
      await request
        .delete(`${baseURL}/api/projects/${copyPid}`, {
          headers: { "X-Auth-Token": TOKEN },
        })
        .catch(() => {});
    }
  }
});
