import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import AuditGlobalView from "@/views/AuditGlobalView.vue";

// AuditView uses auditApi.list when global=false; with global=true it never calls it.
// Mock it anyway to avoid module resolution errors.
vi.mock("@/api/audit", () => ({
  auditApi: { list: vi.fn().mockResolvedValue([]) },
}));

describe("AuditGlobalView", () => {
  it("mounts AuditView with global=true and shows v2.3 placeholder", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/", component: { template: "<div/>" } }],
    });
    await router.push("/");
    const w = mount(AuditGlobalView, { global: { plugins: [router] } });
    expect(w.text()).toContain("全局审计");
    expect(w.text()).toMatch(/v2\.3/);
  });
});
