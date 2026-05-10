import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
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
      scale_adjusted: 332.75,
      effort_pm: { P10: 50, P50: 80, P90: 110 },
      cost_yuan: { P10: 300000, P50: 489180, P90: 700000 },
    }),
    reverse: vi.fn(),
  },
}));

vi.mock("@/api/reports", () => ({
  reportsApi: {
    excelUrl: (id: number) => `/api/reports/excel/${id}`,
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
  id: 1,
  name: "p",
  mode: "forward" as const,
  city: "北京",
  industry: "电子政务",
  stage: "bidding" as const,
  created_at: "",
  updated_at: "",
};

const reverseProject = {
  ...forwardProject,
  id: 2,
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
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    await flushPromises();
    expect(w.text()).toContain("48.92");
    const recommended = w.find("[data-recommended='true']");
    expect(recommended.exists()).toBe(true);
    expect(recommended.attributes("data-band")).toBe("P50");
  });

  it("reverse 模式：显示反算输入区（fieldset + 目标总造价 input + 反算按钮）", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(reverseProject);
    router.push("/projects/2/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: 2 },
      global: { plugins: [createPinia(), router, ElementPlus] },
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
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
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
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    await flushPromises();
    const dlBtn = w.findAll("button").find((b) => b.text().includes("下载 Excel"));
    await dlBtn!.trigger("click");
    await flushPromises();
    expect(reportsApi.download).toHaveBeenCalledWith(1, "p.xlsx");
  });

  it("点击「返回 FP 编辑」→ 路由跳 fp-editor 并带 id", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(forwardProject);
    router.push("/projects/1/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    await flushPromises();
    const backBtn = w.findAll("button").find((b) => b.text() === "返回 FP 编辑");
    expect(backBtn).toBeDefined();
    await backBtn!.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("fp-editor");
    expect(router.currentRoute.value.params.id).toBe("1");
  });

  it("reverse 模式：targetTotal=0 时点反算 → 显示「请输入目标金额」错误", async () => {
    vi.mocked(projectsApi.get).mockResolvedValueOnce(reverseProject);
    router.push("/projects/2/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: 2 },
      global: { plugins: [createPinia(), router, ElementPlus] },
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
      fp_total: { P10: 100, P50: 200, P90: 300 },
      recommended_band: "P50" as const,
    });
    router.push("/projects/2/result");
    await router.isReady();
    const w = mount(ResultView, {
      props: { projectId: 2 },
      global: { plugins: [createPinia(), router, ElementPlus] },
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
      project_id: 2,
      target_total: 1_000_000,
      other_cost: 50_000,
    });
    expect(w.text()).toContain("FP");
  });
});
