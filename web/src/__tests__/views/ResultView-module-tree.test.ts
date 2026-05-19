import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ResultView from "@/views/ResultView.vue";
import { calcApi } from "@/api/calc";
import { projectsApi } from "@/api/projects";
import { aiTasksApi } from "@/api/aiTasks";

vi.mock("@/api/calc", () => ({
  calcApi: { forward: vi.fn(), reverse: vi.fn(), allocate: vi.fn() },
}));
vi.mock("@/api/projects", () => ({
  projectsApi: { get: vi.fn() },
}));
vi.mock("@/api/aiTasks", () => ({
  aiTasksApi: {
    create: vi.fn().mockResolvedValue({ id: "task-rf" }),
    start: vi.fn().mockResolvedValue({ pid: 123 }),
    list: vi.fn().mockResolvedValue([]),
    get: vi.fn(),
  },
}));

const reverseResult = {
  budget_for_dev: 800000,
  budget_for_ops: 0,
  scale_adjusted_bands: { P10: 100, P50: 200, P90: 300 },
  scale_unadjusted_bands: { P10: 80, P50: 165, P90: 250 },
  cf_used: 1.21,
  recommended_band: "P50",
  target_ufp: 165,
  module_allocation: [],
  module_allocation_tree: [
    {
      subsystem: "结算", current_ufp: 100, allocated_ufp: 165,
      delta_ufp: 65, ratio: 1.0,
      children: [
        {
          l1_module: "资金", current_ufp: 100, allocated_ufp: 165,
          delta_ufp: 65, ratio: 1.0,
          children: [
            { l2_module: "查询", current_ufp: 40, allocated_ufp: 66,
              delta_ufp: 26, ratio: 0.4 },
            { l2_module: "对账", current_ufp: 60, allocated_ufp: 99,
              delta_ufp: 39, ratio: 0.6 },
          ],
        },
      ],
    },
  ],
};

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: "/projects/:id/result", component: ResultView, name: "result" }],
});

async function mountResult() {
  (projectsApi.get as ReturnType<typeof vi.fn>).mockResolvedValue({
    id: "p-1", name: "T", mode: "reverse", target_cost: 100,
  });
  (calcApi.reverse as ReturnType<typeof vi.fn>).mockResolvedValue(reverseResult);
  router.push("/projects/p-1/result");
  await router.isReady();
  const w = mount(ResultView, {
    props: { projectId: "p-1" },
    global: { plugins: [createPinia(), router] },
  });
  await flushPromises();
  return w;
}

describe("ResultView — 反算三级模块树", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("渲染三级树节点（子系统/一级/二级）", async () => {
    const w = await mountResult();
    expect(w.text()).toContain("结算");
    expect(w.text()).toContain("资金");
    expect(w.text()).toContain("查询");
    expect(w.text()).toContain("对账");
    expect(w.find(".tree-row-l0").exists()).toBe(true);
    expect(w.findAll(".tree-row-l1").length).toBe(1);
    expect(w.findAll(".tree-row-l2").length).toBe(2);
  });

  it("「按反算补全 FP」按钮触发 reverse_fill AI 任务", async () => {
    const w = await mountResult();
    await w.find("[data-testid='reverse-fill-btn']").trigger("click");
    await flushPromises();
    expect(aiTasksApi.create).toHaveBeenCalledWith("p-1", "reverse_fill");
    expect(aiTasksApi.start).toHaveBeenCalledWith("task-rf");
  });
});
