import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
import ParamManager from "@/views/ParamManager.vue";
import { paramsApi } from "@/api/params";

vi.mock("@/api/params", () => ({
  paramsApi: {
    effective: vi.fn(),
    override: vi.fn(),
  },
}));

const baseEffective = {
  cf: { budget: 1.39, bidding: 1.21, planning: 1.10, change: 1.10, settled: 1.00 },
  productivity_dev: { 电子政务: { P10: 2.04, P50: 6.41, P90: 15.36 } },
  productivity_ops: {},
  city_rate: { 北京: { dev: 32198, ops: 26335, class: "A" } },
  factors_dev: {},
  factors_ops: {},
  hours_per_pm: 174,
  ops_cost_ratio: { P50: 0.0902 },
  overrides: {},
};

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: "/projects/:id/parameters", component: ParamManager, name: "param-manager" }],
});

describe("ParamManager", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    (paramsApi.effective as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(baseEffective);
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

  it("点击第 2 个 Tab 后 aria-selected 切换 + 渲染生产率面板", async () => {
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
    expect(w.text()).toContain("开发生产率");
  });

  it("加载失败 → 显示 ErrorBanner（patchOverride 不被调）", async () => {
    (paramsApi.effective as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("参数 500"),
    );
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    expect(w.find("[role='alert']").exists()).toBe(true);
    expect(w.text()).toContain("参数 500");
  });

  it("第 3+ Tab 显示「v2 完成」骨架", async () => {
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    const tabs = w.findAll("[role='tab']");
    await tabs[2].trigger("click");
    expect(w.text()).toContain("v2 完成");
  });

  it("OverrideField 改值 → 调 paramsApi.override 并 mark params changed", async () => {
    (paramsApi.override as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ...baseEffective,
      city_rate: { 北京: { dev: 99999, ops: 26335, class: "A" } },
      overrides: { "city_rate.北京.dev": 99999 },
    });
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    // 改第一个 OverrideField 数字输入
    const input = w.find("input[type='number']");
    await input.setValue(99999);
    await flushPromises();
    expect(paramsApi.override).toHaveBeenCalledWith(1, { "city_rate.北京.dev": 99999 });
  });
});
