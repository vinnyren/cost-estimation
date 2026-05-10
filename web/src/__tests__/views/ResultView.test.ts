import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
import ResultView from "@/views/ResultView.vue";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    get: vi.fn().mockResolvedValue({
      id: 1,
      name: "p",
      mode: "forward",
      city: "北京",
      industry: "电子政务",
      stage: "bidding",
      created_at: "",
      updated_at: "",
    }),
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
  routes: [{ path: "/projects/:id/result", component: ResultView, name: "result-view" }],
});

describe("ResultView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("forward 模式：显示三档金额卡片，P50 推荐", async () => {
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
});
