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

  it("反向模式：mode='reverse' 时 step 5 显示目标金额输入", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();

    // step 1 → reverse
    const radios = w.findAll("input[type='radio']");
    await radios[1].setValue();
    expect((w.find("[data-test='wizard-next']").element as HTMLButtonElement).disabled).toBe(false);
    await w.find("[data-test='wizard-next']").trigger("click");

    // step 2 → name
    await w.find("input[type='text']").setValue("反向项目");
    await w.find("[data-test='wizard-next']").trigger("click");

    // step 3 → defaults
    await w.find("[data-test='wizard-next']").trigger("click");

    // step 4 → defaults
    await w.find("[data-test='wizard-next']").trigger("click");

    // step 5 → reverse branch should render the target_total + alpha inputs
    expect(w.text()).toContain("目标金额");
    expect(w.text()).toContain("目标总造价");
    expect(w.text()).toContain("α 调整系数");
    // The number inputs for target_total + alpha are present.
    const numberInputs = w.findAll("input[type='number']");
    expect(numberInputs.length).toBe(2);
  });

  it("反向模式 submit：form.target_total 正确映射到 payload.target_cost", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();

    // step 1 → reverse
    const radios = w.findAll("input[type='radio']");
    await radios[1].setValue();
    await w.find("[data-test='wizard-next']").trigger("click");

    // step 2 → name
    await w.find("input[type='text']").setValue("反向项目");
    await w.find("[data-test='wizard-next']").trigger("click");

    // step 3 → defaults
    await w.find("[data-test='wizard-next']").trigger("click");

    // step 4 → defaults
    await w.find("[data-test='wizard-next']").trigger("click");

    // step 5 → fill target_total + alpha. Order: target_total first, alpha second.
    const numberInputs = w.findAll("input[type='number']");
    await numberInputs[0].setValue(800000);
    await numberInputs[1].setValue(1.2);

    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    expect(submitBtn).toBeDefined();
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();

    expect(projectsApi.create).toHaveBeenCalledTimes(1);
    const payload = (projectsApi.create as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0];
    // Mapping: form.target_total → payload.target_cost (the backend field).
    // form.target_total itself must NOT leak into the payload — only the
    // mapped/aliased field does.
    expect(payload).toMatchObject({
      mode: "reverse",
      name: "反向项目",
      target_cost: 800000,
      alpha_dev: 1.2,
    });
    expect(payload).not.toHaveProperty("target_total");
    expect(payload).not.toHaveProperty("alpha");
  });

  it("正向模式 submit：payload 不带 target_cost", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();

    // step 1 → forward (radios[0])
    const radios = w.findAll("input[type='radio']");
    await radios[0].setValue();
    await w.find("[data-test='wizard-next']").trigger("click");

    await w.find("input[type='text']").setValue("正向项目");
    await w.find("[data-test='wizard-next']").trigger("click");
    await w.find("[data-test='wizard-next']").trigger("click");
    await w.find("[data-test='wizard-next']").trigger("click");

    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();

    const payload = (projectsApi.create as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(payload.mode).toBe("forward");
    // forward 模式不应携带 target_cost（条件映射）
    expect(payload.target_cost).toBeUndefined();
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
