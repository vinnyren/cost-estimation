import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import ReportCenterView from "@/views/ReportCenterView.vue";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    list: vi.fn().mockResolvedValue([]),
  },
}));
vi.mock("@/api/reports", () => ({
  reportsApi: { download: vi.fn() },
}));

describe("ReportCenterView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders title and empty table when no projects", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/", component: { template: "<div/>" } }],
    });
    await router.push("/");
    const w = mount(ReportCenterView, { global: { plugins: [router] } });
    await flushPromises();
    expect(w.text()).toContain("报告中心");
    expect(w.find("table.table").exists()).toBe(true);
  });
});
