import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ResultView from "@/views/ResultView.vue";
import { projectsApi } from "@/api/projects";
import { calcApi } from "@/api/calc";
import { reportsApi } from "@/api/reports";
import { functionsApi, type FunctionPoint } from "@/api/functions";

// AllocatorPanel 现在从真实 FP 的 l1_module 生成 drafts —— 提供 dev FP fixture。
const allocFps: FunctionPoint[] = [
  {
    id: "afp-1",
    project_id: "p-2",
    l1_module: "前端",
    category: "EI",
    complexity: "low",
    fp_kind: "dev",
    ufp: 3,
    us: 3,
    source: "manual",
    version: 1,
  },
  {
    id: "afp-2",
    project_id: "p-2",
    l1_module: "后端",
    category: "ILF",
    complexity: "average",
    fp_kind: "dev",
    ufp: 10,
    us: 10,
    source: "manual",
    version: 1,
  },
];

vi.mock("@/api/projects", () => ({
  projectsApi: {
    get: vi.fn(),
  },
}));

vi.mock("@/api/calc", () => ({
  calcApi: {
    forward: vi.fn().mockResolvedValue({
      scale_us: 275,
      scale_adjusted: 332.75,
      cf_used: 1.21,
      effort_dev_hours: { P10: 800, P50: 1600, P90: 2400 },
      effort_ops_hours: { P10: 0, P50: 0, P90: 0 },
      cost_dev_yuan: { P10: 300000, P50: 489180, P90: 700000 },
      cost_ops_yuan: { P10: 0, P50: 0, P90: 0 },
      cost_other_yuan: 0,
      cost_total_yuan: { P10: 300000, P50: 489180, P90: 700000 },
    }),
    reverse: vi.fn(),
    allocate: vi.fn(),
  },
}));

vi.mock("@/api/reports", () => ({
  reportsApi: {
    excelUrl: (id: string) => `/api/reports/excel/${id}`,
    download: vi.fn(),
  },
}));

vi.mock("@/api/functions", () => ({
  functionsApi: {
    list: vi.fn().mockResolvedValue([]),
    patch: vi.fn(),
    create: vi.fn(),
    remove: vi.fn(),
    bulk: vi.fn(),
    snapshots: vi.fn(),
    restore: vi.fn(),
  },
}));

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: "/projects/:id/result", component: ResultView, name: "result-view" },
    {
      path: "/projects/:id/functions",
      component: { template: "<div/>" },
      name: "fp-editor",
    },
  ],
});

const forwardProject = {
  id: "p-1",
  name: "p",
  project_type: "dev_only" as const,
  mode: "forward" as const,
  city: "北京",
  industry: "电子政务",
  phase: "bidding" as const,
  basis_data_ver: "CSBMK®-202510",
  created_at: "",
  updated_at: "",
};

const reverseProject = {
  ...forwardProject,
  id: "p-2",
  mode: "reverse" as const,
};

describe("ResultView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("forward 模式：显示三档金额卡片，P50 推荐", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(forwardProject);
    router.push("/projects/1/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    expect(w.text()).toContain("48.92");
    // v2.2: ResultTrio uses .recommended CSS class (not data-recommended attr)
    const recommended = w.find(".result-card.recommended");
    expect(recommended.exists()).toBe(true);
    // P50 card should contain the recommended pill text
    expect(recommended.text()).toContain("P50");
  });

  it("reverse 模式：显示 3 列反算输入区 + 反算按钮", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(reverseProject);
    router.push("/projects/2/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: "p-2" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    // 单一规模模型 — α 开发占比不再是输入，反算输入只剩 3 列
    expect(w.text()).toContain("反算输入");
    expect(w.text()).toContain("目标总造价");
    expect(w.text()).toContain("其他费用");
    expect(w.text()).toContain("可用预算");
    expect(w.text()).not.toContain("α 开发占比");
    const buttons = w.findAll("button");
    const reverseBtn = buttons.find((b) => b.text() === "反算");
    expect(reverseBtn).toBeDefined();
  });

  it("reverse 模式：可用预算 = target - other（disabled 字段）(v2.4)", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(reverseProject);
    router.push("/projects/2/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: "p-2" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    // 模拟用户输入（number 类型 input）
    const numInputs = w.findAll("input[type='number']");
    expect(numInputs.length).toBeGreaterThanOrEqual(2);
    await numInputs[0].setValue(1500000);
    await numInputs[1].setValue(60000);
    await flushPromises();
    // 可用预算 input（disabled）应为 1,440,000（zh-CN locale 带逗号）
    const budgetInput = w.find("input.field-input[disabled]");
    expect(budgetInput.exists()).toBe(true);
    expect((budgetInput.element as HTMLInputElement).value).toBe("1,440,000");
  });

  it("Excel 下载失败时显示 ErrorBanner（role=alert）", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(forwardProject);
    vi.mocked(reportsApi.download).mockRejectedValueOnce(new Error("网络中断"));
    router.push("/projects/1/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    const buttons = w.findAll("button");
    const dlBtn = buttons.find((b) => b.text().includes("下载 Excel"));
    expect(dlBtn).toBeDefined();
    await dlBtn!.trigger("click");
    await flushPromises();
    await flushPromises();
    expect(w.find("[role='alert']").exists()).toBe(true);
    expect(w.text()).toContain("网络中断");
  });

  it("Excel 下载成功路径：调用 reportsApi.download 并传 projectId+filename", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(forwardProject);
    vi.mocked(reportsApi.download).mockResolvedValueOnce(undefined);
    router.push("/projects/1/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    const dlBtn = w.findAll("button").find((b) => b.text().includes("下载 Excel"));
    await dlBtn!.trigger("click");
    await flushPromises();
    expect(reportsApi.download).toHaveBeenCalledWith("p-1", "p.xlsx");
  });

  it("点击「返回」→ 路由跳 fp-editor 并带 id", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(forwardProject);
    router.push("/projects/1/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    const backBtn = w.findAll("button").find((b) => b.text() === "返回");
    expect(backBtn).toBeDefined();
    await backBtn!.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("fp-editor");
    expect(router.currentRoute.value.params.id).toBe("p-1");
  });

  it("reverse 模式：targetTotal=0 时点反算 → 显示「请输入目标金额」错误", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(reverseProject);
    router.push("/projects/2/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: "p-2" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    const reverseBtn = w.findAll("button").find((b) => b.text() === "反算");
    await reverseBtn!.trigger("click");
    await flushPromises();
    expect(w.text()).toContain("请输入目标金额");
    expect(calcApi.reverse).not.toHaveBeenCalled();
  });

  it("reverse 模式：已有目标造价 → 进页面自动反算（无需再点反算）", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce({
      ...reverseProject,
      target_cost: 400,
    });
    vi.mocked(calcApi.reverse).mockResolvedValue({
      budget_for_dev: 4_000_000,
      budget_for_ops: 0,
      scale_adjusted_bands: { P10: 300, P50: 200, P90: 100 },
      scale_unadjusted_bands: { P10: 240, P50: 160, P90: 80 },
      cf_used: 1.21,
      recommended_band: "P50" as const,
    });
    router.push("/projects/2/result");
    await router.isReady();
    mount(ResultView, {
      props: { projectId: "p-2" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    // 挂载即自动反算，目标 400 万 ×10000 换算成元 = 4,000,000
    expect(calcApi.reverse).toHaveBeenCalledWith({
      project_id: "p-2",
      target_total: 4_000_000,
      other_cost: 0,
    });
  });

  it("reverse 模式：targetTotal>0 → 调 reverse API 并显示三档 FP", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(reverseProject);
    vi.mocked(calcApi.reverse).mockResolvedValueOnce({
      budget_for_dev: 950_000,
      budget_for_ops: 0,
      scale_adjusted_bands: { P10: 300, P50: 200, P90: 100 },
      scale_unadjusted_bands: { P10: 240, P50: 160, P90: 80 },
      cf_used: 1.25,
      recommended_band: "P50" as const,
    });
    router.push("/projects/2/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: "p-2" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    const inputs = w.findAll("input[type='number']");
    await inputs[0].setValue(1_000_000);
    await inputs[1].setValue(50_000);
    const reverseBtn = w.findAll("button").find((b) => b.text() === "反算");
    await reverseBtn!.trigger("click");
    await flushPromises();
    await flushPromises();
    // 目标造价以万元录入 → 调 API 前 ×10000 换算成元
    expect(calcApi.reverse).toHaveBeenCalledWith({
      project_id: "p-2",
      target_total: 10_000_000_000,
      other_cost: 500_000_000,
    });
    expect(w.text()).toContain("FP");
    // v2.4 — ResultTrio 渲染（替代旧 ResultCard × 3）
    await flushPromises();
    const trio = w.find(".result-trio");
    expect(trio.exists()).toBe(true);
  });

  it("reverse 模式：allocator panel 仅在反算结果出现后渲染", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(reverseProject);
    vi.mocked(functionsApi.list).mockResolvedValue(allocFps);
    router.push("/projects/2/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: "p-2" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    // 反算前 — 没有 panel
    expect(w.text()).not.toContain("FP 模块反算分摊");
    // 反算后 — panel 出现
    vi.mocked(calcApi.reverse).mockResolvedValueOnce({
      budget_for_dev: 950_000,
      budget_for_ops: 0,
      scale_adjusted_bands: { P10: 300, P50: 200, P90: 100 },
      scale_unadjusted_bands: { P10: 240, P50: 160, P90: 80 },
      cf_used: 1.25,
      recommended_band: "P50" as const,
    });
    await w.findAll("input[type='number']")[0].setValue(1_000_000);
    const reverseBtn = w.findAll("button").find((b) => b.text() === "反算");
    await reverseBtn!.trigger("click");
    await flushPromises();
    await flushPromises();
    expect(w.text()).toContain("FP 模块反算分摊");
    // AllocatorPanel button text
    const allocBtn = w.findAll("button").find((b) => b.text().includes("生成分摊"));
    expect(allocBtn).toBeDefined();
  });

  it("reverse 模式：forward project 不渲染 allocator panel", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(forwardProject);
    router.push("/projects/1/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    expect(w.text()).not.toContain("AI 模块分摊");
    expect(w.findAll("button").find((b) => b.text().includes("生成分摊"))).toBeUndefined();
  });

  it("AllocatorPanel: 点击「生成分摊」→ 调 calcApi.allocate 并显示分摊结果", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(reverseProject);
    vi.mocked(calcApi.reverse).mockResolvedValueOnce({
      budget_for_dev: 950_000,
      budget_for_ops: 0,
      scale_adjusted_bands: { P10: 300, P50: 200, P90: 100 },
      scale_unadjusted_bands: { P10: 240, P50: 160, P90: 80 },
      cf_used: 1.21,
      recommended_band: "P50" as const,
    });
    vi.mocked(functionsApi.list).mockResolvedValue(allocFps);
    vi.mocked(calcApi.allocate).mockResolvedValueOnce({
      items: [
        { name: "前端", us: 66.12, locked: false, audit_tag: "budget_derived" },
        { name: "后端", us: 99.17, locked: false, audit_tag: "budget_derived" },
      ],
      validation: { recalc_total_us: 165.29, recalc_total_adjusted: 200.0, error_pct: 0.0 },
    });

    router.push("/projects/2/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: "p-2" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    await w.findAll("input[type='number']")[0].setValue(1_000_000);
    await w.findAll("button").find((b) => b.text() === "反算")!.trigger("click");
    await flushPromises();
    await flushPromises();
    const allocBtn = w.findAll("button").find((b) => b.text().includes("生成分摊"));
    expect(allocBtn).toBeDefined();
    await allocBtn!.trigger("click");
    await flushPromises();
    await flushPromises();
    // AllocatorPanel calls allocate with default drafts (前端 weight=1, 后端 weight=1.5)
    expect(calcApi.allocate).toHaveBeenCalledWith({
      project_id: "p-2",
      target_us: 200,
      cf: 1.21,
      drafts: expect.arrayContaining([
        expect.objectContaining({ name: "前端" }),
        expect.objectContaining({ name: "后端" }),
      ]),
    });
    // Results rendered in AllocatorPanel table
    expect(w.text()).toContain("66.12");
    expect(w.text()).toContain("99.17");
    // Consistency banner
    expect(w.text()).toContain("误差");
  });

  it("AllocatorPanel: allocate API 失败 → 显示 amber banner 提示", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(reverseProject);
    vi.mocked(calcApi.reverse).mockResolvedValueOnce({
      budget_for_dev: 950_000,
      budget_for_ops: 0,
      scale_adjusted_bands: { P10: 300, P50: 200, P90: 100 },
      scale_unadjusted_bands: { P10: 240, P50: 160, P90: 80 },
      cf_used: 1.21,
      recommended_band: "P50" as const,
    });
    vi.mocked(functionsApi.list).mockResolvedValue(allocFps);
    vi.mocked(calcApi.allocate).mockRejectedValueOnce(new Error("分摊服务不可用"));

    router.push("/projects/2/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: "p-2" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    await w.findAll("input[type='number']")[0].setValue(1_000_000);
    await w.findAll("button").find((b) => b.text() === "反算")!.trigger("click");
    await flushPromises();
    await flushPromises();
    const allocBtn = w.findAll("button").find((b) => b.text().includes("生成分摊"));
    await allocBtn!.trigger("click");
    await flushPromises();
    expect(w.text()).toContain("分摊服务不可用");
  });
});
