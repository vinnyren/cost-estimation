import { describe, it, expect, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import AuditGlobalView from "@/views/AuditGlobalView.vue";

vi.mock("@/api/audit", () => ({
  auditApi: {
    list: vi.fn().mockResolvedValue([]),
    listGlobal: vi.fn().mockResolvedValue([]),
  },
}));

describe("AuditGlobalView", () => {
  it("mounts AuditView with global=true and renders 全局审计时间线", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/", component: { template: "<div/>" } }],
    });
    await router.push("/");
    const w = mount(AuditGlobalView, { global: { plugins: [router] } });
    await flushPromises();
    expect(w.text()).toContain("全局审计");
    expect(w.text()).not.toMatch(/将在 v2\.3 上线/);
  });
});
