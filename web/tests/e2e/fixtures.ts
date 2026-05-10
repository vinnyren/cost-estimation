import { test as base, expect } from "@playwright/test";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

type CostFixtures = {
  freshProject: { id: string; name: string };
};

export const test = base.extend<CostFixtures>({
  freshProject: async ({ request, baseURL }, use) => {
    const name = `e2e-${Date.now()}`;
    const created = await request.post(`${baseURL}/api/projects`, {
      headers: { "X-Auth-Token": TOKEN },
      data: {
        name,
        project_type: "dev_only",
        mode: "forward",
        city: "北京",
        industry: "电子政务",
        phase: "bidding",
        basis_data_ver: "CSBMK®-202510",
      },
    });
    expect(created.ok()).toBeTruthy();
    const body = await created.json();
    const id: string = body.data.id;

    await use({ id, name });

    // teardown
    await request.delete(`${baseURL}/api/projects/${id}`, {
      headers: { "X-Auth-Token": TOKEN },
    });
  },
});

export { expect };
