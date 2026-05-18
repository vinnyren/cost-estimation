import { describe, it, expect, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import AuditView from "@/views/AuditView.vue";

vi.mock("@/api/audit", () => ({
  auditApi: {
    list: vi.fn().mockResolvedValue([]),
    listGlobal: vi.fn().mockResolvedValue([]),
  },
}));
import { auditApi } from "@/api/audit";

const makeRouter = () =>
  createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/", component: { template: "<div/>" } }],
  });

describe("AuditView global 分支", () => {
  it("global=true 时调 auditApi.listGlobal", async () => {
    const router = makeRouter();
    await router.push("/");
    mount(AuditView, {
      props: { global: true },
      global: { plugins: [router] },
    });
    await flushPromises();
    expect(auditApi.listGlobal).toHaveBeenCalled();
  });
});
