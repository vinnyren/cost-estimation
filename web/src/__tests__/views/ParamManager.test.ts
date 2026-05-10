import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
import ParamManager from "@/views/ParamManager.vue";

vi.mock("@/api/params", () => ({
  paramsApi: {
    effective: vi.fn().mockResolvedValue({
      cf: { budget: 1.39, bidding: 1.21, planning: 1.10, change: 1.10, settled: 1.00 },
      productivity_dev: { 电子政务: { P10: 2.04, P50: 6.41, P90: 15.36 } },
      productivity_ops: {},
      city_rate: { 北京: { dev: 32198, ops: 26335, class: "A" } },
      factors_dev: {},
      factors_ops: {},
      hours_per_pm: 174,
      ops_cost_ratio: { P50: 0.0902 },
      overrides: {},
    }),
    override: vi.fn(),
  },
}));

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: "/projects/:id/parameters", component: ParamManager, name: "param-manager" }],
});

describe("ParamManager", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("加载后显示 6 个 Tab", async () => {
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    const tabs = w.findAll("[role='tab']");
    expect(tabs.length).toBeGreaterThanOrEqual(6);
  });

  it("点击第 2 个 Tab 后 aria-selected 切换", async () => {
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    const tabs = w.findAll("[role='tab']");
    expect(tabs[0].attributes("aria-selected")).toBe("true");
    await tabs[1].trigger("click");
    expect(tabs[1].attributes("aria-selected")).toBe("true");
    expect(tabs[0].attributes("aria-selected")).toBe("false");
  });
});
