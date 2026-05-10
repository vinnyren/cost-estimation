import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
import ResultView from "@/views/ResultView.vue";
import { projectsApi } from "@/api/projects";
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
    { path: "/projects/:id/fp", component: { template: "<div/>" }, name: "fp-editor" },
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
});
