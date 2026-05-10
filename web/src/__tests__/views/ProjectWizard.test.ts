import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
import ProjectWizard from "@/views/ProjectWizard.vue";
import { projectsApi } from "@/api/projects";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    create: vi.fn(),
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

const mountWizard = () =>
  mount(ProjectWizard, {
    global: { plugins: [createPinia(), router, ElementPlus] },
  });

describe("ProjectWizard", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    (projectsApi.create as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "p-99",
      name: "new",
      project_type: "dev_only",
      mode: "forward",
      city: "北京",
      industry: "电子政务",
      phase: "bidding",
      basis_data_ver: "CSBMK®-202510",
      created_at: "",
      updated_at: "",
    });
  });

  it("初始处于第 1 步：模式选择", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    expect(w.text()).toContain("选择评估模式");
  });

  it("name 为空时不能进入下一步", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    const nextBtn = w.find("[data-test='wizard-next']");
    expect((nextBtn.element as HTMLButtonElement).disabled).toBe(true);
  });

  it("逐步前进 next/back 后，第 5 步 forward 模式 submit → 调 create + 跳路由", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();

    // step 1 → 选 forward 后 next
    await w.findAll("input[type='radio']")[0].setValue();
    await w.find("[data-test='wizard-next']").trigger("click");

    // step 2 → 填名称
    await w.find("input[type='text']").setValue("项目甲");
    await w.find("[data-test='wizard-next']").trigger("click");

    // step 3 → 默认值即合法（北京 + 电子政务）
    await w.find("[data-test='wizard-next']").trigger("click");

    // step 4 → 默认 bidding 即合法
    await w.find("[data-test='wizard-next']").trigger("click");

    // step 5 forward → submit
    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    expect(submitBtn).toBeDefined();
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();

    expect(projectsApi.create).toHaveBeenCalled();
    expect(router.currentRoute.value.name).toBe("fp-editor");
  });

  it("back 按钮回到上一步", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.findAll("input[type='radio']")[0].setValue();
    await w.find("[data-test='wizard-next']").trigger("click");
    expect(w.text()).toContain("项目名称");
    const backBtn = w.findAll("button").find((b) => b.text() === "上一步");
    await backBtn!.trigger("click");
    expect(w.text()).toContain("选择评估模式");
  });

  it("submit 失败 → 显示 errorMsg（role=alert）", async () => {
    (projectsApi.create as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("名称重复"),
    );
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();

    await w.findAll("input[type='radio']")[0].setValue();
    await w.find("[data-test='wizard-next']").trigger("click");
    await w.find("input[type='text']").setValue("dup");
    await w.find("[data-test='wizard-next']").trigger("click");
    await w.find("[data-test='wizard-next']").trigger("click");
    await w.find("[data-test='wizard-next']").trigger("click");

    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();
    expect(w.text()).toContain("名称重复");
  });
});
