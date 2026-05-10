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
      props: { projectId: "p-1" },
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
      props: { projectId: "p-1" },
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
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    expect(w.find("[role='alert']").exists()).toBe(true);
    expect(w.text()).toContain("参数 500");
  });

  it("未实装 Tab（规模变更 / 快照）显示「v2 完成」骨架", async () => {
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    const tabs = w.findAll("[role='tab']");
    // tabs[4] = scale_change（GAP-B 已实装 factors_dev/_ops，仅规模变更/快照仍是骨架）
    await tabs[4].trigger("click");
    expect(w.text()).toContain("v2 完成");
  });

  it("开发因子 Tab → 渲染 FactorTable 表 + 改值调 override 用 factors_dev.{name}.{level} 路径 (GAP-B)", async () => {
    const effWithFactors = {
      ...baseEffective,
      factors_dev: {
        app_type: { 业务处理: 1.0, 软件集成: 1.2 },
        platform: { JAVA: 1.0, C: 1.5 },
      },
    };
    (paramsApi.effective as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(effWithFactors);
    (paramsApi.override as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ...effWithFactors,
      factors_dev: {
        app_type: { 业务处理: 1.0, 软件集成: 1.5 },
        platform: { JAVA: 1.0, C: 1.5 },
      },
      overrides: { "factors_dev.app_type.软件集成": 1.5 },
    });
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    const tabs = w.findAll("[role='tab']");
    await tabs[2].trigger("click"); // factors_dev
    await flushPromises();

    // 渲染 factor 卡片 (data-factor) + 中文标签
    expect(w.find('[data-factor="app_type"]').exists()).toBe(true);
    expect(w.find('[data-factor="platform"]').exists()).toBe(true);
    expect(w.text()).toContain("应用类型");
    expect(w.text()).toContain("运行平台");

    // 找到 app_type/软件集成 输入（值 1.20）并改成 1.5
    const card = w.find('[data-factor="app_type"]');
    const inputs = card.findAll("input[type='number']");
    const target = inputs.find(
      (i) => (i.element as HTMLInputElement).value === "1.20",
    )!;
    expect(target).toBeTruthy();
    await target.setValue("1.5");
    await target.trigger("change");
    await flushPromises();

    expect(paramsApi.override).toHaveBeenCalledWith("p-1", {
      "factors_dev.app_type.软件集成": 1.5,
    });
  });

  it("运维因子 Tab → 渲染 FactorTable + 改值用 factors_ops.{name}.{level} 路径 (GAP-B)", async () => {
    const effWithOps = {
      ...baseEffective,
      factors_ops: {
        update_freq: { quarterly: 0.95, monthly: 1.0, frequent: 1.12 },
      },
    };
    (paramsApi.effective as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(effWithOps);
    (paramsApi.override as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ...effWithOps,
      overrides: { "factors_ops.update_freq.frequent": 1.25 },
    });
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    const tabs = w.findAll("[role='tab']");
    await tabs[3].trigger("click"); // factors_ops
    await flushPromises();

    expect(w.find('[data-factor="update_freq"]').exists()).toBe(true);
    expect(w.text()).toContain("更新频率");

    const card = w.find('[data-factor="update_freq"]');
    const inputs = card.findAll("input[type='number']");
    const target = inputs.find(
      (i) => (i.element as HTMLInputElement).value === "1.12",
    )!;
    await target.setValue("1.25");
    await target.trigger("change");
    await flushPromises();

    expect(paramsApi.override).toHaveBeenCalledWith("p-1", {
      "factors_ops.update_freq.frequent": 1.25,
    });
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
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    // 改第一个 OverrideField 数字输入
    const input = w.find("input[type='number']");
    await input.setValue(99999);
    await flushPromises();
    expect(paramsApi.override).toHaveBeenCalledWith("p-1", { "city_rate.北京.dev": 99999 });
  });
});
