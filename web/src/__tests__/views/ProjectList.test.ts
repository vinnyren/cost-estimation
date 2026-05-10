import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ProjectList from "@/views/ProjectList.vue";
import ElementPlus from "element-plus";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    list: vi.fn(),
    create: vi.fn(),
    remove: vi.fn(),
  },
}));

import { projectsApi } from "@/api/projects";

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
    (projectsApi.list as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise(() => {}),
    );
    const w = mountList();
    await flushPromises();
    expect(w.find("[data-test='skeleton-row']").exists()).toBe(true);
  });

  it("Empty 态显示 CTA", async () => {
    (projectsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ items: [] });
    const w = mountList();
    await flushPromises();
    expect(w.text()).toContain("新建第一个项目");
  });

  it("Success 态显示项目卡片 + total_cost 经 formatCost 格式化为 万元", async () => {
    (projectsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 1,
          name: "test-p1",
          mode: "forward",
          city: "北京",
          industry: "电子政务",
          stage: "bidding",
          total_cost: 250_000,
          total_fp: 100,
          created_at: "",
          updated_at: "",
        },
      ],
    });
    const w = mountList();
    await flushPromises();
    expect(w.text()).toContain("test-p1");
    expect(w.text()).toContain("正向");
    // formatCost(250000) = (250000/10000).toFixed(2) = "25.00"
    expect(w.text()).toContain("25.00");
    expect(w.text()).toContain("万元");
  });

  it("Error 态显示 banner + 重试", async () => {
    (projectsApi.list as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("network down"),
    );
    const w = mountList();
    await flushPromises();
    expect(w.find("[role='alert']").exists()).toBe(true);
    expect(w.find("[data-test='retry']").exists()).toBe(true);
  });

  it("点击新建按钮 → 路由跳到 project-wizard", async () => {
    (projectsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ items: [] });
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
    (projectsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 42,
          name: "p",
          mode: "forward",
          city: "北京",
          industry: "电子政务",
          stage: "bidding",
          created_at: "",
          updated_at: "",
        },
      ],
    });
    await router.push("/");
    await router.isReady();
    const w = mountList();
    await flushPromises();
    const openBtn = w.findAll("button").find((b) => b.text() === "打开");
    expect(openBtn).toBeDefined();
    await openBtn!.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("fp-editor");
    expect(router.currentRoute.value.params.id).toBe("42");
  });

  it("点击「删除」→ confirm=false 时不调 remove API", async () => {
    (projectsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 7,
          name: "p",
          mode: "forward",
          city: "北京",
          industry: "电子政务",
          stage: "bidding",
          created_at: "",
          updated_at: "",
        },
      ],
    });
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const w = mountList();
    await flushPromises();
    const delBtn = w.findAll("button").find((b) => b.text() === "删除");
    await delBtn!.trigger("click");
    expect(confirmSpy).toHaveBeenCalled();
    expect(projectsApi.remove).not.toHaveBeenCalled();
  });

  it("点击「删除」→ confirm=true 时调 remove API", async () => {
    (projectsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 7,
          name: "p",
          mode: "forward",
          city: "北京",
          industry: "电子政务",
          stage: "bidding",
          created_at: "",
          updated_at: "",
        },
      ],
    });
    (projectsApi.remove as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const w = mountList();
    await flushPromises();
    const delBtn = w.findAll("button").find((b) => b.text() === "删除");
    await delBtn!.trigger("click");
    await flushPromises();
    expect(projectsApi.remove).toHaveBeenCalledWith(7);
  });
});
