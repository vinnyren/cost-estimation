import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
import ProjectWizard from "@/views/ProjectWizard.vue";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    create: vi.fn().mockResolvedValue({
      id: 99,
      name: "new",
      mode: "forward",
      city: "北京",
      industry: "电子政务",
      stage: "bidding",
      created_at: "",
      updated_at: "",
    }),
  },
}));

const fpRoute = {
  path: "/projects/:id/functions",
  name: "fp-editor",
  component: { template: "<div/>" },
};
const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: "/projects/new", component: ProjectWizard, name: "project-wizard" },
    fpRoute,
  ],
});

describe("ProjectWizard", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
  });

  it("初始处于第 1 步：模式选择", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mount(ProjectWizard, {
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    expect(w.text()).toContain("选择评估模式");
  });

  it("name 为空时不能进入下一步", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mount(ProjectWizard, {
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    const nextBtn = w.find("[data-test='wizard-next']");
    expect((nextBtn.element as HTMLButtonElement).disabled).toBe(true);
  });
});
