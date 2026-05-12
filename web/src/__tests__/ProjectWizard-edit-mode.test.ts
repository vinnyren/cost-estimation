import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia, setActivePinia } from "pinia";
import ProjectWizard from "@/views/ProjectWizard.vue";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    get: vi.fn().mockResolvedValue({
      id: "p-edit-test",
      name: "已存在项目",
      city: "上海",
      industry: "金融",
      phase: "bidding",
      project_type: "dev_and_ops",
      mode: "reverse",
      target_cost: 1500000,
      other_cost: 25000,
      client: "测试客户",
      evaluator: "测试评估方",
      alpha_dev: 0.85,
      include_ops: true,
      factors_dev: { app_type: "业务处理" },
      factors_ops: {},
      basis_data_ver: "CSBMK-202510",
      fp_method: "nesma_estimated",
      created_at: "2026-05-12T00:00:00Z",
      updated_at: "2026-05-12T00:00:00Z",
    }),
    update: vi.fn().mockResolvedValue({ id: "p-edit-test" }),
    create: vi.fn(),
    list: vi.fn().mockResolvedValue([]),
    query: vi.fn().mockResolvedValue({ data: [], meta: { total: 0, page: 1, size: 50 } }),
  },
}));

vi.mock("@/api/params", () => ({
  paramsApi: {
    global: vi.fn().mockResolvedValue({
      cf: { budget: 1.5, bidding: 1.21, planning: 1.1, change: 1.05, settled: 1.0 },
      productivity_dev: {},
      productivity_ops: {},
      city_rate: {},
      factors_dev: {},
      factors_ops: {},
      hours_per_pm: 174,
      ops_cost_ratio: { P50: 0.15 },
    }),
    effective: vi.fn().mockResolvedValue({
      cf: { budget: 1.5, bidding: 1.21, planning: 1.1, change: 1.05, settled: 1.0 },
      productivity_dev: {},
      productivity_ops: {},
      city_rate: {},
      factors_dev: {},
      factors_ops: {},
      hours_per_pm: 174,
      ops_cost_ratio: { P50: 0.15 },
    }),
  },
}));

import { projectsApi } from "@/api/projects";

describe("ProjectWizard edit mode (v2.5)", () => {
  let router: ReturnType<typeof createRouter>;

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/", component: { template: "<div/>" } },
        { path: "/projects/new", name: "project-wizard", component: ProjectWizard },
        { path: "/projects/:id/edit", name: "project-edit", component: ProjectWizard },
        { path: "/projects/:id/functions", name: "fp-editor", component: { template: "<div/>" } },
      ],
    });
  });

  it("with projectId prop: fetches project and shows 编辑项目设定 title", async () => {
    await router.push("/projects/p-edit-test/edit");
    await router.isReady();
    const w = mount(ProjectWizard, {
      props: { projectId: "p-edit-test" },
      global: {
        plugins: [router],
        stubs: { AlphaSlider: true, PhaseCfPreview: true, FactorDropdown: true },
      },
    });
    await flushPromises();
    expect(projectsApi.get).toHaveBeenCalledWith("p-edit-test");
    expect(w.text()).toContain("编辑项目设定");
  });

  it("without projectId prop: shows 新建项目 title and does not call get", async () => {
    await router.push("/projects/new");
    await router.isReady();
    const w = mount(ProjectWizard, {
      global: {
        plugins: [router],
        stubs: { AlphaSlider: true, PhaseCfPreview: true, FactorDropdown: true },
      },
    });
    await flushPromises();
    expect(projectsApi.get).not.toHaveBeenCalled();
    expect(w.text()).toContain("新建项目");
  });
});
