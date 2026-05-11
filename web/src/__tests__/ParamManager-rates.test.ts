import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ParamManager from "@/views/ParamManager.vue";
import { paramsApi } from "@/api/params";

// Mock 与现有 ParamManager.test.ts 同一策略：替换 paramsApi
vi.mock("@/api/params", () => ({
  paramsApi: {
    effective: vi.fn(),
    override: vi.fn(),
  },
}));

const baseEffective = {
  cf: { budget: 1.39, bidding: 1.21, planning: 1.10, change: 1.10, settled: 1.00 },
  productivity_dev: {
    电子政务: { P10: 2.04, P50: 6.41, P90: 15.36 },
  },
  productivity_ops: {
    电子政务: { P10: 1.5, P50: 4.2, P90: 9.8 },
  },
  city_rate: {
    北京: { dev: 32198, ops: 26335, class: "A" },
    上海: { dev: 30500, ops: 25100, class: "A" },
  },
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

describe("ParamManager — 城市费率 ops 列 + 运维生产率 ops 表 (GAP-D)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    (paramsApi.effective as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(baseEffective);
  });

  it("rate 面板对每个城市同时渲染 dev / ops 字段", async () => {
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();

    const rows = w.findAll("[data-testid='city-rate-row']");
    expect(rows.length).toBeGreaterThanOrEqual(2);

    const beijing = rows.find((r) => r.text().includes("北京"));
    expect(beijing).toBeTruthy();
    // dev + ops 两个输入都必须出现
    const inputs = beijing!.findAll("input[type='number']");
    expect(inputs.length).toBe(2);
    const values = inputs.map((i) => (i.element as HTMLInputElement).value);
    expect(values).toContain("32198"); // dev
    expect(values).toContain("26335"); // ops
  });

  it("productivity 面板同时渲染 productivity_dev 和 productivity_ops 两张表", async () => {
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();

    const tabs = w.findAll("[role='tab']");
    await tabs[1].trigger("click"); // productivity tab
    await flushPromises();

    const text = w.text();
    expect(text).toContain("开发生产率");
    expect(text).toContain("运维生产率");

    // 运维生产率值出现
    const inputs = w.findAll("input[type='number']");
    const values = inputs.map((i) => (i.element as HTMLInputElement).value);
    expect(values).toContain("4.2"); // productivity_ops 电子政务 P50
    expect(values).toContain("1.5"); // productivity_ops 电子政务 P10
  });

  it("修改城市 ops 费率 → 调 paramsApi.override 用 city_rate.{city}.ops 路径", async () => {
    (paramsApi.override as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ...baseEffective,
      city_rate: {
        ...baseEffective.city_rate,
        北京: { dev: 32198, ops: 88888, class: "A" },
      },
      overrides: { "city_rate.北京.ops": 88888 },
    });
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();

    const rows = w.findAll("[data-testid='city-rate-row']");
    const beijing = rows.find((r) => r.text().includes("北京"))!;
    const inputs = beijing.findAll("input[type='number']");
    // 第二个 input 为 ops
    const opsInput = inputs.find(
      (i) => (i.element as HTMLInputElement).value === "26335",
    )!;
    await opsInput.setValue(88888);
    await flushPromises();

    expect(paramsApi.override).toHaveBeenCalledWith("p-1", {
      "city_rate.北京.ops": 88888,
    });
  });

  it("修改 productivity_ops 值 → 调 paramsApi.override 用 productivity_ops.{ind}.{band}", async () => {
    (paramsApi.override as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ...baseEffective,
      productivity_ops: {
        电子政务: { P10: 1.5, P50: 7.7, P90: 9.8 },
      },
      overrides: { "productivity_ops.电子政务.P50": 7.7 },
    });
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();

    const tabs = w.findAll("[role='tab']");
    await tabs[1].trigger("click");
    await flushPromises();

    // 找到值为 4.2 的输入（productivity_ops 电子政务 P50）
    const inputs = w.findAll("input[type='number']");
    const target = inputs.find(
      (i) => (i.element as HTMLInputElement).value === "4.2",
    )!;
    await target.setValue(7.7);
    await flushPromises();

    expect(paramsApi.override).toHaveBeenCalledWith("p-1", {
      "productivity_ops.电子政务.P50": 7.7,
    });
  });
});
