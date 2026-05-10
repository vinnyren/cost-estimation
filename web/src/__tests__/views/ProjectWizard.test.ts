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

vi.mock("@/api/params", () => ({
  paramsApi: {
    effective: vi.fn().mockResolvedValue({ cf: { bidding: 1.21 } }),
    global: vi.fn().mockResolvedValue({ cf: { bidding: 1.21 } }),
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

/**
 * NOTE (T13 — Wizard 5 → 7 steps skeleton):
 *   Steps reorganized: 1 基础信息 / 2 项目类型 / 3 阶段 / 4 正/反向 /
 *   5 开发因子 / 6 运维因子 / 7 确认。
 *   Steps 2-7 are placeholders until T14-T18 fill them in. The end-to-end
 *   submit flow (mode → target_cost mapping, error display) will be re-asserted
 *   once those tasks land. For now we cover what survives the skeleton: step 1
 *   inputs, advance gating, and (with default form state) a step 7 submit.
 */

describe("ProjectWizard skeleton (T13)", () => {
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

  it("初始处于第 1 步：基础信息", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    expect(w.text()).toContain("基础信息");
    expect(w.find('input[name="name"]').exists()).toBe(true);
  });

  it("name 为空时不能进入下一步", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    const nextBtn = w.find("[data-test='wizard-next']");
    expect((nextBtn.element as HTMLButtonElement).disabled).toBe(true);
  });

  it("填了 name 之后可以前进，back 返回上一步", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("项目甲");
    const nextBtn = w.find("[data-test='wizard-next']");
    expect((nextBtn.element as HTMLButtonElement).disabled).toBe(false);
    await nextBtn.trigger("click");
    expect(w.text()).toContain("项目类型");
    const backBtn = w.findAll("button").find((b) => b.text() === "上一步");
    await backBtn!.trigger("click");
    expect(w.text()).toContain("基础信息");
  });

  it("步骤指示器渲染 7 个 step，data-active 跟随 currentStep", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    const steps = w.findAll('[data-testid="wizard-step"]');
    expect(steps.length).toBe(7);
    expect(steps[0].attributes("data-active")).toBe("true");
    expect(steps[1].attributes("data-active")).toBe("false");

    await w.find('input[name="name"]').setValue("项目甲");
    await w.find("[data-test='wizard-next']").trigger("click");
    const stepsAfter = w.findAll('[data-testid="wizard-step"]');
    expect(stepsAfter[0].attributes("data-active")).toBe("false");
    expect(stepsAfter[0].attributes("data-done")).toBe("true");
    expect(stepsAfter[1].attributes("data-active")).toBe("true");
  });

  it("step 1 含 client + evaluator 字段", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    expect(w.find('input[name="client"]').exists()).toBe(true);
    expect(w.find('input[name="evaluator"]').exists()).toBe(true);
  });

  it("默认 forward 模式逐步前进到 step 7 → submit 调 create + 跳路由", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();

    // step 1 → 填名称
    await w.find('input[name="name"]').setValue("项目甲");
    await w.find("[data-test='wizard-next']").trigger("click");

    // step 2-6 都是 placeholder（默认值合法）→ 连续 next
    for (let i = 0; i < 5; i++) {
      const btn = w.find("[data-test='wizard-next']");
      await btn.trigger("click");
    }

    // step 7 → 创建项目
    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    expect(submitBtn).toBeDefined();
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();

    expect(projectsApi.create).toHaveBeenCalled();
    expect(router.currentRoute.value.name).toBe("fp-editor");
  });

  it("submit 失败 → 显示 errorMsg（role=alert）", async () => {
    (projectsApi.create as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("名称重复"),
    );
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();

    await w.find('input[name="name"]').setValue("dup");
    for (let i = 0; i < 6; i++) {
      await w.find("[data-test='wizard-next']").trigger("click");
    }

    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();
    expect(w.text()).toContain("名称重复");
  });

  it("默认 forward submit 不携带 target_cost", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();

    await w.find('input[name="name"]').setValue("正向项目");
    for (let i = 0; i < 6; i++) {
      await w.find("[data-test='wizard-next']").trigger("click");
    }
    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();

    const payload = (projectsApi.create as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(payload.mode).toBe("forward");
    expect(payload.target_cost).toBeUndefined();
  });

  // TODO(T14-T18): mode 选择 UI 落地后再补 reverse 模式 target_total → target_cost
  // 映射、α 输入、project_type 等端到端用例。
});
