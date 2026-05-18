import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import ProjectList from "@/views/ProjectList.vue";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    query: vi.fn(),
    exportProjects: vi.fn(),
    importProjects: vi.fn(),
  },
}));
vi.mock("@/api/stats", () => ({
  statsApi: { getProjectStats: vi.fn().mockResolvedValue(null) },
}));

import { projectsApi } from "@/api/projects";

const mkProject = (id: string, name: string) => ({
  id,
  name,
  project_type: "dev_only",
  mode: "forward",
  city: "北京",
  industry: "电子政务",
  phase: "bidding",
  basis_data_ver: "CSBMK®-202510",
  created_at: "2026-05-18T00:00:00Z",
  updated_at: "2026-05-18T00:00:00Z",
});

const makeRouter = () =>
  createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: { template: "<div/>" } },
      { path: "/projects/:id/functions", component: { template: "<div/>" }, name: "fp-editor" },
      { path: "/projects/new", component: { template: "<div/>" }, name: "project-wizard" },
    ],
  });

const mountList = async () => {
  const router = makeRouter();
  await router.push("/");
  const w = mount(ProjectList, { global: { plugins: [router] } });
  await flushPromises();
  return w;
};

describe("ProjectList 选择态 + 导出导入 (v2.7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (projectsApi.query as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [mkProject("p-1", "项目甲"), mkProject("p-2", "项目乙")],
      meta: { total: 2, page: 1, size: 50 },
    });
  });

  it("表格视图每行有复选框，表头有全选", async () => {
    const w = await mountList();
    expect(w.find('[data-testid="select-all"]').exists()).toBe(true);
    expect(w.findAll('[data-testid="row-checkbox"]').length).toBe(2);
  });

  it("未选中任何项目时批量导出按钮 disabled", async () => {
    const w = await mountList();
    const exportBtn = w.find('[data-testid="export-btn"]');
    expect((exportBtn.element as HTMLButtonElement).disabled).toBe(true);
  });

  it("勾选单行后批量导出可点并调 exportProjects", async () => {
    (projectsApi.exportProjects as ReturnType<typeof vi.fn>).mockResolvedValue({
      version: "2.7",
      exported_at: "x",
      projects: [],
    });
    const w = await mountList();
    await w.findAll('[data-testid="row-checkbox"]')[0].setValue(true);
    const exportBtn = w.find('[data-testid="export-btn"]');
    expect((exportBtn.element as HTMLButtonElement).disabled).toBe(false);
    await exportBtn.trigger("click");
    await flushPromises();
    expect(projectsApi.exportProjects).toHaveBeenCalledWith(["p-1"]);
  });

  it("全选勾选后选中所有项目", async () => {
    const w = await mountList();
    await w.find('[data-testid="select-all"]').setValue(true);
    const exportBtn = w.find('[data-testid="export-btn"]');
    expect((exportBtn.element as HTMLButtonElement).disabled).toBe(false);
  });

  it("导入文件后调 importProjects 并重新加载列表", async () => {
    (projectsApi.importProjects as ReturnType<typeof vi.fn>).mockResolvedValue({
      imported: 1,
      project_ids: ["n-1"],
    });
    const w = await mountList();
    const bundle = { version: "2.7", exported_at: "x", projects: [] };
    const file = new File([JSON.stringify(bundle)], "import.json", {
      type: "application/json",
    });
    const input = w.find('[data-testid="import-input"]');
    Object.defineProperty(input.element, "files", { value: [file] });
    await input.trigger("change");
    await flushPromises();
    expect(projectsApi.importProjects).toHaveBeenCalledWith(bundle);
    expect((projectsApi.query as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThanOrEqual(2);
  });
});
