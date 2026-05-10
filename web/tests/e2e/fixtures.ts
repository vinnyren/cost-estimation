import { test as base, expect } from "@playwright/test";

const TOKEN = process.env.E2E_AUTH_TOKEN ?? "e2e-token";

type CostFixtures = {
  freshProject: { id: number; name: string };
};

export const test = base.extend<CostFixtures>({
  freshProject: async ({ request, baseURL }, use) => {
    const name = `e2e-${Date.now()}`;
    const created = await request.post(`${baseURL}/api/projects`, {
      headers: { "X-Auth-Token": TOKEN },
      data: {
        name,
        mode: "forward",
        city: "北京",
        industry: "电子政务",
        stage: "bidding",
      },
    });
    expect(created.ok()).toBeTruthy();
    const body = await created.json();
    const id = body.data.id;

    await use({ id, name });

    // teardown
    await request.delete(`${baseURL}/api/projects/${id}`, {
      headers: { "X-Auth-Token": TOKEN },
    });
  },
});

export { expect };
