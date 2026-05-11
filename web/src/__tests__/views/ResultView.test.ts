import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ResultView from "@/views/ResultView.vue";
import { projectsApi } from "@/api/projects";
import { calcApi } from "@/api/calc";
import { reportsApi } from "@/api/reports";

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

  it("reverse 模式：显示反算输入区（fieldset + 目标总造价 input + 反算按钮）", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(reverseProject);
    router.push("/projects/2/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: "p-2" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    expect(w.find("fieldset").exists()).toBe(true);
    expect(w.text()).toContain("反算输入");
    expect(w.text()).toContain("目标总造价");
    const buttons = w.findAll("button");
    const reverseBtn = buttons.find((b) => b.text() === "反算");
    expect(reverseBtn).toBeDefined();
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

  it("reverse 模式：targetTotal>0 → 调 reverse API 并显示三档 FP", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(reverseProject);
    vi.mocked(calcApi.reverse).mockResolvedValueOnce({
      budget_for_dev: 950_000,
      budget_for_ops: 0,
      scale_adjusted_bands: { P10: 300, P50: 200, P90: 100 },
      scale_unadjusted_bands: { P10: 240, P50: 160, P90: 80 },
      scale_adjusted_ops_bands: { P10: 0, P50: 0, P90: 0 },
      scale_unadjusted_ops_bands: { P10: 0, P50: 0, P90: 0 },
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
    expect(calcApi.reverse).toHaveBeenCalledWith({
      project_id: "p-2",
      target_total: 1_000_000,
      other_cost: 50_000,
    });
    expect(w.text()).toContain("FP");
  });

  it("reverse 模式：allocator panel 仅在反算结果出现后渲染", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(reverseProject);
    router.push("/projects/2/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: "p-2" },
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();
    await flushPromises();
    // 反算前 — 没有 panel
    expect(w.text()).not.toContain("AI 模块分摊");
    // 反算后 — panel 出现
    vi.mocked(calcApi.reverse).mockResolvedValueOnce({
      budget_for_dev: 950_000,
      budget_for_ops: 0,
      scale_adjusted_bands: { P10: 300, P50: 200, P90: 100 },
      scale_unadjusted_bands: { P10: 240, P50: 160, P90: 80 },
      scale_adjusted_ops_bands: { P10: 0, P50: 0, P90: 0 },
      scale_unadjusted_ops_bands: { P10: 0, P50: 0, P90: 0 },
      cf_used: 1.25,
      recommended_band: "P50" as const,
    });
    await w.findAll("input[type='number']")[0].setValue(1_000_000);
    const reverseBtn = w.findAll("button").find((b) => b.text() === "反算");
    await reverseBtn!.trigger("click");
    await flushPromises();
    await flushPromises();
    expect(w.text()).toContain("AI 模块分摊");
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
      scale_adjusted_ops_bands: { P10: 0, P50: 0, P90: 0 },
      scale_unadjusted_ops_bands: { P10: 0, P50: 0, P90: 0 },
      cf_used: 1.21,
      recommended_band: "P50" as const,
    });
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
      scale_adjusted_ops_bands: { P10: 0, P50: 0, P90: 0 },
      scale_unadjusted_ops_bands: { P10: 0, P50: 0, P90: 0 },
      cf_used: 1.21,
      recommended_band: "P50" as const,
    });
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
