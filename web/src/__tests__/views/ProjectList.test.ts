import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ProjectList from "@/views/ProjectList.vue";
import ElementPlus from "element-plus";

// v2.0 T20 — ProjectList drives projectsApi.query() directly. The store is no
// longer in the listing path, so tests mock query() (returning the new
// {data, meta} shape) instead of list().
vi.mock("@/api/projects", () => ({
  projectsApi: {
    list: vi.fn(),
    query: vi.fn(),
    create: vi.fn(),
    remove: vi.fn(),
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
  created_at: "",
  updated_at: "",
  ...overrides,
});

const okResult = (
  data: Array<ReturnType<typeof project>>,
  meta: { total: number; page?: number; size?: number } = { total: data.length },
) => ({
  data,
  meta: { page: 1, size: 20, ...meta },
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
      plugins: [createPinia(), router, ElementPlus],
    },
  });

describe("ProjectList", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
  });

  it("Loading 态显示 skeleton", async () => {
    queryMock().mockReturnValue(new Promise(() => {}));
    const w = mountList();
    await flushPromises();
    expect(w.find("[data-test='skeleton-row']").exists()).toBe(true);
  });

  it("Empty 态显示 CTA", async () => {
    queryMock().mockResolvedValue(okResult([], { total: 0 }));
    const w = mountList();
    await flushPromises();
    expect(w.text()).toContain("新建第一个项目");
  });

  it("Success 态显示项目卡片 + total_cost 经 formatCost 格式化为 万元", async () => {
    queryMock().mockResolvedValue(
      okResult([project({ total_cost: 250_000, total_fp: 100 })], { total: 1 }),
    );
    const w = mountList();
    await flushPromises();
    expect(w.text()).toContain("test-p1");
    expect(w.text()).toContain("正向");
    expect(w.text()).toContain("25.00");
    expect(w.text()).toContain("万元");
  });

  it("Error 态显示 banner + 重试", async () => {
    queryMock().mockRejectedValue(new Error("network down"));
    const w = mountList();
    await flushPromises();
    expect(w.find("[role='alert']").exists()).toBe(true);
    expect(w.find("[data-test='retry']").exists()).toBe(true);
  });

  it("点击新建按钮 → 路由跳到 project-wizard", async () => {
    queryMock().mockResolvedValue(okResult([], { total: 0 }));
    await router.push("/");
    await router.isReady();
    const w = mountList();
    await flushPromises();
    const newBtn = w.findAll("button").find((b) => b.text() === "新建项目");
    expect(newBtn).toBeDefined();
    await newBtn!.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("project-wizard");
  });

  it("点击「打开」→ 路由跳到 fp-editor 并带 id", async () => {
    queryMock().mockResolvedValue(okResult([project({ id: "p-42", name: "p" })], { total: 1 }));
    await router.push("/");
    await router.isReady();
    const w = mountList();
    await flushPromises();
    const openBtn = w.findAll("button").find((b) => b.text() === "打开");
    expect(openBtn).toBeDefined();
    await openBtn!.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("fp-editor");
    expect(router.currentRoute.value.params.id).toBe("p-42");
  });

  it("点击「删除」→ confirm=false 时不调 remove API", async () => {
    queryMock().mockResolvedValue(okResult([project({ id: "p-7", name: "p" })], { total: 1 }));
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const w = mountList();
    await flushPromises();
    const delBtn = w.findAll("button").find((b) => b.text() === "删除");
    await delBtn!.trigger("click");
    expect(confirmSpy).toHaveBeenCalled();
    expect(projectsApi.remove).not.toHaveBeenCalled();
  });

  it("点击「删除」→ confirm=true 时调 remove API", async () => {
    queryMock().mockResolvedValue(okResult([project({ id: "p-7", name: "p" })], { total: 1 }));
    removeMock().mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const w = mountList();
    await flushPromises();
    const delBtn = w.findAll("button").find((b) => b.text() === "删除");
    await delBtn!.trigger("click");
    await flushPromises();
    expect(projectsApi.remove).toHaveBeenCalledWith("p-7");
  });
});

describe("ProjectList toolbar (T20)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
    queryMock().mockResolvedValue(okResult([], { total: 0 }));
  });

  it("初次挂载时用默认 filter 调 query", async () => {
    const w = mountList();
    await flushPromises();
    expect(queryMock()).toHaveBeenCalledTimes(1);
    const opts = queryMock().mock.calls[0][0];
    expect(opts).toMatchObject({
      sort: "created_at",
      order: "desc",
      page: 1,
      size: 20,
    });
    expect(opts.q).toBeUndefined();
    expect(opts.city).toBeUndefined();
    w.unmount();
  });

  it("输入搜索关键字 → 防抖后用 q 调 query", async () => {
    vi.useFakeTimers();
    try {
      const w = mountList();
      await flushPromises();
      const input = w.find('[data-testid="filter-q"]');
      await input.setValue("智慧");
      // Before the debounce window, query should not have been re-called yet.
      expect(queryMock()).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(300);
      await flushPromises();
      expect(queryMock()).toHaveBeenCalledTimes(2);
      const lastCall = queryMock().mock.calls.at(-1);
      expect(lastCall?.[0]).toMatchObject({ q: "智慧", page: 1 });
      w.unmount();
    } finally {
      vi.useRealTimers();
    }
  });

  it("切换城市筛选 → 立刻用 city 调 query 并重置到第 1 页", async () => {
    const w = mountList();
    await flushPromises();
    await w.find('[data-testid="filter-city"]').setValue("北京");
    await flushPromises();
    expect(queryMock()).toHaveBeenCalledTimes(2);
    const opts = queryMock().mock.calls.at(-1)?.[0];
    expect(opts).toMatchObject({ city: "北京", page: 1 });
    w.unmount();
  });

  it("切换行业筛选 → 用 industry 调 query", async () => {
    const w = mountList();
    await flushPromises();
    await w.find('[data-testid="filter-industry"]').setValue("金融");
    await flushPromises();
    const opts = queryMock().mock.calls.at(-1)?.[0];
    expect(opts).toMatchObject({ industry: "金融" });
    w.unmount();
  });

  it("切换阶段筛选 → 用 phase 调 query", async () => {
    const w = mountList();
    await flushPromises();
    await w.find('[data-testid="filter-phase"]').setValue("settled");
    await flushPromises();
    const opts = queryMock().mock.calls.at(-1)?.[0];
    expect(opts).toMatchObject({ phase: "settled" });
    w.unmount();
  });

  it("切换排序字段 → 用新 sort 调 query", async () => {
    const w = mountList();
    await flushPromises();
    await w.find('[data-testid="filter-sort"]').setValue("name");
    await flushPromises();
    const opts = queryMock().mock.calls.at(-1)?.[0];
    expect(opts).toMatchObject({ sort: "name" });
    w.unmount();
  });

  it("点击排序方向按钮 → order 在 asc / desc 之间切换", async () => {
    const w = mountList();
    await flushPromises();
    const orderBtn = w.find('[data-testid="filter-order"]');
    expect(orderBtn.text()).toContain("降序");

    await orderBtn.trigger("click");
    await flushPromises();
    expect(queryMock().mock.calls.at(-1)?.[0]).toMatchObject({ order: "asc" });
    expect(w.find('[data-testid="filter-order"]').text()).toContain("升序");

    await w.find('[data-testid="filter-order"]').trigger("click");
    await flushPromises();
    expect(queryMock().mock.calls.at(-1)?.[0]).toMatchObject({ order: "desc" });
    w.unmount();
  });

  it("total > pageSize 时显示分页，可翻到下一页", async () => {
    // Page 1: 20 items, total 25 → "下一页" enabled.
    const page1Items = Array.from({ length: 20 }, (_, i) =>
      project({ id: `p-${i + 1}`, name: `项目${i + 1}` }),
    );
    queryMock()
      .mockResolvedValueOnce(okResult(page1Items, { total: 25, page: 1 }))
      .mockResolvedValueOnce(
        okResult(
          Array.from({ length: 5 }, (_, i) =>
            project({ id: `p-${i + 21}`, name: `项目${i + 21}` }),
          ),
          { total: 25, page: 2 },
        ),
      );

    const w = mountList();
    await flushPromises();
    const next = w.find('[data-testid="pagination-next"]');
    expect(next.exists()).toBe(true);
    expect((next.element as HTMLButtonElement).disabled).toBe(false);

    await next.trigger("click");
    await flushPromises();
    expect(queryMock()).toHaveBeenCalledTimes(2);
    const opts = queryMock().mock.calls.at(-1)?.[0];
    expect(opts).toMatchObject({ page: 2 });
    w.unmount();
  });

  it("total <= pageSize 时不显示分页", async () => {
    queryMock().mockResolvedValue(
      okResult([project({ id: "p-only", name: "唯一项目" })], { total: 1 }),
    );
    const w = mountList();
    await flushPromises();
    expect(w.find('[data-testid="pagination-prev"]').exists()).toBe(false);
    expect(w.find('[data-testid="pagination-next"]').exists()).toBe(false);
    w.unmount();
  });
});
