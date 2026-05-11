import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ProjectList from "@/views/ProjectList.vue";

// v2.2 T14 — ProjectList v2.2 重做：KPI cards + filter bar + table/card 双视图
// 测试覆盖：loading/empty/success/error 四态 + 导航 + action menu

vi.mock("@/api/projects", () => ({
  projectsApi: {
    list: vi.fn(),
    query: vi.fn(),
    create: vi.fn(),
    remove: vi.fn(),
    copy: vi.fn(),
  },
}));

vi.mock("@/api/stats", () => ({
  statsApi: {
    getProjectStats: vi.fn().mockResolvedValue({
      counts: { total: 0, draft: 0, in_progress: 0, archived: 0, delivered: 0 },
      monthly_count: 0,
      monthly_p50_sum: 0,
      monthly_growth_pct: 0,
    }),
  },
}));

import { projectsApi } from "@/api/projects";

type QueryMock = ReturnType<typeof vi.fn>;
const queryMock = () => projectsApi.query as unknown as QueryMock;
const removeMock = () => projectsApi.remove as unknown as ReturnType<typeof vi.fn>;

const project = (overrides: Record<string, unknown> = {}) => ({
  id: "p-1",
  name: "test-p1",
  mode: "forward" as const,
  city: "北京",
  industry: "电子政务",
  phase: "bidding" as const,
  project_type: "dev_only" as const,
  basis_data_ver: "CSBMK®-202510",
  created_at: "2025-01-01T00:00:00",
  updated_at: "2025-01-02T00:00:00",
  ...overrides,
});

const okResult = (
  data: Array<ReturnType<typeof project>>,
  meta: { total: number; page?: number; size?: number } = { total: data.length },
) => ({
  data,
  meta: { page: 1, size: 50, ...meta },
});

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: "/", component: ProjectList, name: "project-list" },
    { path: "/projects/new", component: { template: "<div/>" }, name: "project-wizard" },
    {
      path: "/projects/:id/functions",
      component: { template: "<div/>" },
      name: "fp-editor",
    },
  ],
});

const mountList = () =>
  mount(ProjectList, {
    global: {
      plugins: [createPinia(), router],
    },
  });

describe("ProjectList v2.2", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
    // 重置 stats mock（resetAllMocks 会清掉，需要重新设置）
    (projectsApi.query as unknown as QueryMock).mockResolvedValue(okResult([]));
  });

  it("Loading 态显示 skeleton", async () => {
    (projectsApi.query as unknown as QueryMock).mockReturnValue(new Promise(() => {}));
    const w = mountList();
    await flushPromises();
    expect(w.find("[data-test='skeleton-row']").exists()).toBe(true);
  });

  it("Empty 态显示 CTA", async () => {
    (projectsApi.query as unknown as QueryMock).mockResolvedValue(okResult([], { total: 0 }));
    const w = mountList();
    await flushPromises();
    expect(w.text()).toContain("新建第一个项目");
  });

  it("Success 态显示项目行 + total_cost 格式化（万元）", async () => {
    (projectsApi.query as unknown as QueryMock).mockResolvedValue(
      okResult([project({ total_cost: 250_000, total_fp: 100 })], { total: 1 }),
    );
    const w = mountList();
    await flushPromises();
    expect(w.text()).toContain("test-p1");
    // v2.2: 正向估算
    expect(w.text()).toContain("正向估算");
    // ¥25.00万
    expect(w.text()).toContain("25.00");
    expect(w.text()).toContain("万");
  });

  it("Error 态显示 banner + 重试", async () => {
    (projectsApi.query as unknown as QueryMock).mockRejectedValue(new Error("network down"));
    const w = mountList();
    await flushPromises();
    expect(w.find("[role='alert']").exists()).toBe(true);
    expect(w.find("[data-test='retry']").exists()).toBe(true);
  });

  it("点击新建按钮 → 路由跳到 project-wizard", async () => {
    (projectsApi.query as unknown as QueryMock).mockResolvedValue(okResult([], { total: 0 }));
    await router.push("/");
    await router.isReady();
    const w = mountList();
    await flushPromises();
    // v2.2: btn 文字是"+ 新建项目"
    const newBtn = w.findAll("button").find(
      (b) => b.text().includes("新建项目") && !b.text().includes("新建第一个"),
    );
    expect(newBtn).toBeDefined();
    await newBtn!.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("project-wizard");
  });

  it("点击 row-link 行 → 路由跳到 fp-editor 并带 id", async () => {
    (projectsApi.query as unknown as QueryMock).mockResolvedValue(
      okResult([project({ id: "p-42", name: "p" })], { total: 1 }),
    );
    await router.push("/");
    await router.isReady();
    const w = mountList();
    await flushPromises();
    // v2.2: row-link 替代旧"打开"按钮
    const row = w.find("tr.row-link");
    expect(row.exists()).toBe(true);
    await row.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("fp-editor");
    expect(router.currentRoute.value.params.id).toBe("p-42");
  });

  // v2.0 T21 — delete moved into ProjectActionMenu (⋯ menu on each card).
  it("点击 ⋯ → 删除 → confirm=false 时不调 remove API", async () => {
    (projectsApi.query as unknown as QueryMock).mockResolvedValue(
      okResult([project({ id: "p-7", name: "p" })], { total: 1 }),
    );
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const w = mountList();
    await flushPromises();
    await w.find('[data-testid="action-menu-trigger"]').trigger("click");
    await w.find('[data-testid="action-menu-delete"]').trigger("click");
    expect(confirmSpy).toHaveBeenCalled();
    expect(projectsApi.remove).not.toHaveBeenCalled();
  });

  it("点击 ⋯ → 删除 → confirm=true 时调 remove API", async () => {
    (projectsApi.query as unknown as QueryMock).mockResolvedValue(
      okResult([project({ id: "p-7", name: "p" })], { total: 1 }),
    );
    removeMock().mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const w = mountList();
    await flushPromises();
    await w.find('[data-testid="action-menu-trigger"]').trigger("click");
    await w.find('[data-testid="action-menu-delete"]').trigger("click");
    await flushPromises();
    expect(projectsApi.remove).toHaveBeenCalledWith("p-7");
  });

  it("初次挂载时调 query（page=1, size=50）", async () => {
    (projectsApi.query as unknown as QueryMock).mockResolvedValue(okResult([], { total: 0 }));
    const w = mountList();
    await flushPromises();
    expect(queryMock()).toHaveBeenCalledTimes(1);
    const opts = queryMock().mock.calls[0][0];
    expect(opts).toMatchObject({ page: 1, size: 50 });
    w.unmount();
  });

  it("草稿状态：无 total_fp 的项目显示状态草稿", async () => {
    (projectsApi.query as unknown as QueryMock).mockResolvedValue(
      okResult([project({ total_fp: undefined, total_cost: undefined })], { total: 1 }),
    );
    const w = mountList();
    await flushPromises();
    expect(w.text()).toContain("草稿");
  });

  it("已计算状态：有 total_fp 和 total_cost 显示状态已计算", async () => {
    (projectsApi.query as unknown as QueryMock).mockResolvedValue(
      okResult([project({ total_fp: 100, total_cost: 500_000 })], { total: 1 }),
    );
    const w = mountList();
    await flushPromises();
    expect(w.text()).toContain("已计算");
  });
});
