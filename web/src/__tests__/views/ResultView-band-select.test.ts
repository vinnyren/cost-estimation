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
    patch: vi.fn().mockResolvedValue({}),
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
      trace: {
        us: 275,
        cf: 1.21,
        s_adjusted: 332.75,
        pdr_p50: 15.0,
        dev_factor: 1.0,
        eff_pm_p50: 22.18,
        eff_hours_p50: 1600,
        f_city: 22059,
        ops_plus_other: 0,
        total_p50: 489180,
      },
    }),
    reverse: vi.fn(),
    allocate: vi.fn(),
  },
}));

vi.mock("@/api/reports", () => ({
  reportsApi: {
    excelUrl: (id: string) => `/api/reports/excel/${id}`,
    download: vi.fn().mockResolvedValue(undefined),
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
    { path: "/projects/:id/functions", component: { template: "<div/>" }, name: "fp-editor" },
  ],
});

const forwardProject = {
  id: "p-1",
  name: "test-project",
  project_type: "dev_only" as const,
  assessment_kind: "development" as const,
  mode: "forward" as const,
  city: "北京",
  industry: "电子政务",
  phase: "bidding" as const,
  basis_data_ver: "CSBMK®-202510",
  created_at: "",
  updated_at: "",
};

async function mountForward(projectOverrides = {}) {
  vi.mocked(projectsApi.get).mockResolvedValueOnce({ ...forwardProject, ...projectOverrides });
  router.push("/projects/p-1/result");
  await router.isReady();
  const w = mount(ResultView, {
    props: { projectId: "p-1" },
    global: { plugins: [createPinia(), router] },
  });
  await flushPromises();
  await flushPromises();
  return w;
}

describe("ResultView — 三档卡片选择", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    // Re-apply default mock after clearAllMocks
    vi.mocked(projectsApi.patch).mockResolvedValue({} as never);
    vi.mocked(reportsApi.download).mockResolvedValue(undefined);
  });

  it("渲染三个卡片，data-testid 存在", async () => {
    const w = await mountForward();
    expect(w.find("[data-testid='tier-card-P10']").exists()).toBe(true);
    expect(w.find("[data-testid='tier-card-P50']").exists()).toBe(true);
    expect(w.find("[data-testid='tier-card-P90']").exists()).toBe(true);
  });

  it("默认选中 P50（项目无 selected_band）", async () => {
    const w = await mountForward();
    const p50Card = w.find("[data-testid='tier-card-P50']");
    expect(p50Card.attributes("data-selected")).toBe("true");
    expect(p50Card.attributes("aria-pressed")).toBe("true");
    expect(w.find("[data-testid='tier-card-P10']").attributes("data-selected")).toBe("false");
    expect(w.find("[data-testid='tier-card-P90']").attributes("data-selected")).toBe("false");
  });

  it("项目 selected_band=P90 → 初始选中 P90", async () => {
    const w = await mountForward({ selected_band: "P90" });
    expect(w.find("[data-testid='tier-card-P90']").attributes("data-selected")).toBe("true");
    expect(w.find("[data-testid='tier-card-P50']").attributes("data-selected")).toBe("false");
  });

  it("点击 P90 卡片 → emit select → projectsApi.patch 被调用 { selected_band: 'P90' }", async () => {
    const w = await mountForward();
    await w.find("[data-testid='tier-card-P90']").trigger("click");
    await flushPromises();
    expect(projectsApi.patch).toHaveBeenCalledWith("p-1", { selected_band: "P90" });
    // Card now selected
    expect(w.find("[data-testid='tier-card-P90']").attributes("data-selected")).toBe("true");
  });

  it("选择 P90 后「计算路径详解」标题更新为 P90 乐观档", async () => {
    const w = await mountForward();
    await w.find("[data-testid='tier-card-P90']").trigger("click");
    await flushPromises();
    expect(w.text()).toContain("P90 保守档");
    expect(w.text()).not.toContain("P50 推荐档");
  });

  it("选择 P90 后「计算路径详解」显示 P90 总造价（70万）而非 P50（48.9万）", async () => {
    const w = await mountForward();
    // Before selection: P50 total 489,180 元 = 48.92 万
    expect(w.text()).toContain("P50 推荐档");
    await w.find("[data-testid='tier-card-P90']").trigger("click");
    await flushPromises();
    // P90 total = 700,000 元 → pipeline grid shows "700,000"
    expect(w.text()).toContain("700,000");
    // P50 total (489,180) should no longer be prominent in section heading
    // The section title now says P90 保守档
    expect(w.text()).toContain("P90 保守档");
  });

  it("选择 P90 后点击下载，reportsApi.download 以 band='P90' 调用", async () => {
    const w = await mountForward();
    await w.find("[data-testid='tier-card-P90']").trigger("click");
    await flushPromises();
    const dlBtn = w.findAll("button").find((b) => b.text().includes("下载 Excel"));
    expect(dlBtn).toBeDefined();
    await dlBtn!.trigger("click");
    await flushPromises();
    expect(reportsApi.download).toHaveBeenCalledWith("p-1", "test-project.xlsx", "P90");
  });

  it("patch 失败不阻断本地选择状态", async () => {
    vi.mocked(projectsApi.patch).mockRejectedValueOnce(new Error("网络错误"));
    const w = await mountForward();
    await w.find("[data-testid='tier-card-P10']").trigger("click");
    await flushPromises();
    // Local state still updates even if patch failed
    expect(w.find("[data-testid='tier-card-P10']").attributes("data-selected")).toBe("true");
  });

  it("键盘 Enter 键触发选择", async () => {
    const w = await mountForward();
    const p10Card = w.find("[data-testid='tier-card-P10']");
    await p10Card.trigger("keydown", { key: "Enter" });
    await flushPromises();
    expect(projectsApi.patch).toHaveBeenCalledWith("p-1", { selected_band: "P10" });
    expect(p10Card.attributes("data-selected")).toBe("true");
  });
});

describe("ResultTrio 组件 — 独立渲染", () => {
  it("selectedBand prop 标记正确卡片为 selected，其余为 false", async () => {
    const ResultTrio = (await import("@/components/result/ResultTrio.vue")).default;
    const w = mount(ResultTrio, {
      props: {
        tiers: [
          { key: "P10" as const, label: "乐观", cost: 300000, recommended: false, unit: "yuan" as const },
          { key: "P50" as const, label: "中位", cost: 489180, recommended: true, unit: "yuan" as const },
          { key: "P90" as const, label: "保守", cost: 700000, recommended: false, unit: "yuan" as const },
        ],
        selectedBand: "P10" as const,
      },
    });
    expect(w.find("[data-testid='tier-card-P10']").attributes("data-selected")).toBe("true");
    expect(w.find("[data-testid='tier-card-P50']").attributes("data-selected")).toBe("false");
    expect(w.find("[data-testid='tier-card-P90']").attributes("data-selected")).toBe("false");
  });

  it("点击卡片 emit select 事件，带正确 band key", async () => {
    const ResultTrio = (await import("@/components/result/ResultTrio.vue")).default;
    const w = mount(ResultTrio, {
      props: {
        tiers: [
          { key: "P10" as const, label: "乐观", cost: 300000, recommended: false, unit: "yuan" as const },
          { key: "P50" as const, label: "中位", cost: 489180, recommended: true, unit: "yuan" as const },
          { key: "P90" as const, label: "保守", cost: 700000, recommended: false, unit: "yuan" as const },
        ],
        selectedBand: "P50" as const,
      },
    });
    await w.find("[data-testid='tier-card-P90']").trigger("click");
    expect(w.emitted("select")).toBeTruthy();
    expect(w.emitted("select")![0]).toEqual(["P90"]);
  });

  it("推荐卡片有 recommended class，选中卡片有 selected class", async () => {
    const ResultTrio = (await import("@/components/result/ResultTrio.vue")).default;
    const w = mount(ResultTrio, {
      props: {
        tiers: [
          { key: "P10" as const, label: "乐观", cost: 300000, recommended: false, unit: "yuan" as const },
          { key: "P50" as const, label: "中位", cost: 489180, recommended: true, unit: "yuan" as const },
          { key: "P90" as const, label: "保守", cost: 700000, recommended: false, unit: "yuan" as const },
        ],
        selectedBand: "P10" as const,
      },
    });
    expect(w.find("[data-testid='tier-card-P50']").classes()).toContain("recommended");
    expect(w.find("[data-testid='tier-card-P10']").classes()).toContain("selected");
    // P50 is recommended but NOT selected
    expect(w.find("[data-testid='tier-card-P50']").classes()).not.toContain("selected");
  });

  it("卡片和推荐同时成立时，两个 class 都有", async () => {
    const ResultTrio = (await import("@/components/result/ResultTrio.vue")).default;
    const w = mount(ResultTrio, {
      props: {
        tiers: [
          { key: "P50" as const, label: "中位", cost: 489180, recommended: true, unit: "yuan" as const },
        ],
        selectedBand: "P50" as const,
      },
    });
    const card = w.find("[data-testid='tier-card-P50']");
    expect(card.classes()).toContain("recommended");
    expect(card.classes()).toContain("selected");
    expect(card.attributes("aria-pressed")).toBe("true");
  });
});
