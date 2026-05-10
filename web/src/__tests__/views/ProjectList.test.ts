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

  it("Success 态显示项目卡片", async () => {
    (projectsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 1,
          name: "test-p1",
          mode: "forward",
          city: "北京",
          industry: "电子政务",
          stage: "bidding",
          created_at: "",
          updated_at: "",
        },
      ],
    });
    const w = mountList();
    await flushPromises();
    expect(w.text()).toContain("test-p1");
    expect(w.text()).toContain("正向");
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
});
