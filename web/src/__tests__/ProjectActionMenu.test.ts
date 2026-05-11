// v2.0 T21 — Unit tests for ProjectActionMenu (GAP-I / GAP-J 前端).
//
// Covers the three responsibilities of the row-level overflow menu:
//   1. open/close interaction (trigger toggles, outside click closes);
//   2. dispatch — each menu item calls the right API and emits the right event;
//   3. routing — "审计日志" pushes to /projects/:id/audit and copy navigates
//      to the new project's FP editor after a successful copy.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import ProjectActionMenu from "@/components/ProjectActionMenu.vue";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    copy: vi.fn(),
    remove: vi.fn(),
  },
}));

import { projectsApi } from "@/api/projects";

type CopyMock = ReturnType<typeof vi.fn>;
type RemoveMock = ReturnType<typeof vi.fn>;
const copyMock = () => projectsApi.copy as unknown as CopyMock;
const removeMock = () => projectsApi.remove as unknown as RemoveMock;

const makeRouter = () =>
  createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: { template: "<div/>" } },
      { path: "/projects/:id/audit", component: { template: "<div/>" }, name: "project-audit" },
      { path: "/projects/:id/functions", component: { template: "<div/>" }, name: "fp-editor" },
    ],
  });

const mountMenu = (router = makeRouter()) =>
  mount(ProjectActionMenu, {
    props: { projectId: "p1", projectName: "测试项目" },
    global: { plugins: [router] },
  });

describe("ProjectActionMenu", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("初始未打开，点击 trigger 后弹出菜单", async () => {
    const w = mountMenu();
    expect(w.find('[data-testid="action-menu"]').exists()).toBe(false);
    await w.find('[data-testid="action-menu-trigger"]').trigger("click");
    expect(w.find('[data-testid="action-menu"]').exists()).toBe(true);
  });

  it("再次点击 trigger 关闭菜单", async () => {
    const w = mountMenu();
    const trigger = w.find('[data-testid="action-menu-trigger"]');
    await trigger.trigger("click");
    expect(w.find('[data-testid="action-menu"]').exists()).toBe(true);
    await trigger.trigger("click");
    expect(w.find('[data-testid="action-menu"]').exists()).toBe(false);
  });

  it("点击审计 → 路由跳到 /projects/:id/audit", async () => {
    const router = makeRouter();
    const w = mountMenu(router);
    await w.find('[data-testid="action-menu-trigger"]').trigger("click");
    await w.find('[data-testid="action-menu-audit"]').trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.path).toBe("/projects/p1/audit");
  });

  it("点击复制 → prompt 返回名字时调 copy API + emit copied + 跳转", async () => {
    copyMock().mockResolvedValue({ id: "new-id" });
    const promptSpy = vi.spyOn(window, "prompt").mockReturnValue("克隆名");
    const router = makeRouter();
    const w = mountMenu(router);
    await w.find('[data-testid="action-menu-trigger"]').trigger("click");
    await w.find('[data-testid="action-menu-copy"]').trigger("click");
    await flushPromises();
    expect(promptSpy).toHaveBeenCalled();
    expect(projectsApi.copy).toHaveBeenCalledWith("p1", "克隆名");
    expect(w.emitted("copied")).toBeTruthy();
    expect(router.currentRoute.value.path).toBe("/projects/new-id/functions");
  });

  it("点击复制 → prompt 取消（返回 null）时不调 API", async () => {
    vi.spyOn(window, "prompt").mockReturnValue(null);
    const w = mountMenu();
    await w.find('[data-testid="action-menu-trigger"]').trigger("click");
    await w.find('[data-testid="action-menu-copy"]').trigger("click");
    await flushPromises();
    expect(projectsApi.copy).not.toHaveBeenCalled();
    expect(w.emitted("copied")).toBeFalsy();
  });

  it("点击复制 → prompt 返回空白字符串时不调 API", async () => {
    vi.spyOn(window, "prompt").mockReturnValue("   ");
    const w = mountMenu();
    await w.find('[data-testid="action-menu-trigger"]').trigger("click");
    await w.find('[data-testid="action-menu-copy"]').trigger("click");
    await flushPromises();
    expect(projectsApi.copy).not.toHaveBeenCalled();
  });

  it("点击删除 → confirm=true 时调 remove API + emit deleted", async () => {
    removeMock().mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const w = mountMenu();
    await w.find('[data-testid="action-menu-trigger"]').trigger("click");
    await w.find('[data-testid="action-menu-delete"]').trigger("click");
    await flushPromises();
    expect(projectsApi.remove).toHaveBeenCalledWith("p1");
    expect(w.emitted("deleted")).toBeTruthy();
  });

  it("点击删除 → confirm=false 时不调 API", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const w = mountMenu();
    await w.find('[data-testid="action-menu-trigger"]').trigger("click");
    await w.find('[data-testid="action-menu-delete"]').trigger("click");
    await flushPromises();
    expect(projectsApi.remove).not.toHaveBeenCalled();
    expect(w.emitted("deleted")).toBeFalsy();
  });
});
