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

  // TODO(T15-T18): mode 选择 UI 落地后再补 reverse 模式 target_total → target_cost
  // 映射、α 输入等端到端用例。
});

/**
 * NOTE (T14 — Wizard step 2 项目类型 + alpha + include_ops):
 *   Step 2 落地：project_type radio 三选一 / include_ops checkbox 联动 /
 *   AlphaSlider 仅在 dev_and_ops 时显示。
 */

describe("Wizard step 2 — project_type / alpha / include_ops (T14)", () => {
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

  async function gotoStep2() {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("项目甲");
    await w.find("[data-test='wizard-next']").trigger("click");
    return w;
  }

  it("初始进入 step 2：项目类型 radio 三选一可见", async () => {
    const w = await gotoStep2();
    const radios = w.findAll('input[type="radio"][name="project_type"]');
    expect(radios.length).toBe(3);
    expect(w.text()).toContain("仅开发");
    expect(w.text()).toContain("仅运维");
    expect(w.text()).toContain("开发 + 运维");
  });

  it("dev_only 默认：AlphaSlider 不显示，include_ops checkbox 显示且未选中", async () => {
    const w = await gotoStep2();
    expect(w.findComponent({ name: "AlphaSlider" }).exists()).toBe(false);
    const cb = w.find('input[type="checkbox"][name="include_ops"]');
    expect(cb.exists()).toBe(true);
    expect((cb.element as HTMLInputElement).checked).toBe(false);
  });

  it("选择 dev_and_ops：AlphaSlider 出现，include_ops 被强制为 true 且 disabled", async () => {
    const w = await gotoStep2();
    const radios = w.findAll('input[type="radio"][name="project_type"]');
    const devOps = radios.find((r) => (r.element as HTMLInputElement).value === "dev_and_ops")!;
    await devOps.setValue();
    await flushPromises();

    expect(w.findComponent({ name: "AlphaSlider" }).exists()).toBe(true);
    const cb = w.find('input[type="checkbox"][name="include_ops"]');
    expect((cb.element as HTMLInputElement).checked).toBe(true);
    expect((cb.element as HTMLInputElement).disabled).toBe(true);
  });

  it("dev_and_ops → 切回 dev_only：AlphaSlider 消失，alpha 重置 1.0，include_ops 重置 false", async () => {
    const w = await gotoStep2();
    const radios = w.findAll('input[type="radio"][name="project_type"]');
    const devOps = radios.find((r) => (r.element as HTMLInputElement).value === "dev_and_ops")!;
    await devOps.setValue();
    await flushPromises();
    expect(w.findComponent({ name: "AlphaSlider" }).exists()).toBe(true);

    const devOnly = radios.find((r) => (r.element as HTMLInputElement).value === "dev_only")!;
    await devOnly.setValue();
    await flushPromises();

    expect(w.findComponent({ name: "AlphaSlider" }).exists()).toBe(false);
    const cb = w.find('input[type="checkbox"][name="include_ops"]');
    expect((cb.element as HTMLInputElement).checked).toBe(false);

    // 走到 step 7 查 alpha 是否回到 1.0
    for (let i = 0; i < 5; i++) {
      await w.find("[data-test='wizard-next']").trigger("click");
    }
    expect(w.text()).toContain("\"alpha\": 1");
  });

  it("选择 ops_only：include_ops checkbox 隐藏（强制为 true 但不展示），AlphaSlider 不显示", async () => {
    const w = await gotoStep2();
    const radios = w.findAll('input[type="radio"][name="project_type"]');
    const opsOnly = radios.find((r) => (r.element as HTMLInputElement).value === "ops_only")!;
    await opsOnly.setValue();
    await flushPromises();

    expect(w.findComponent({ name: "AlphaSlider" }).exists()).toBe(false);
    expect(w.find('input[type="checkbox"][name="include_ops"]').exists()).toBe(false);
  });

  it("AlphaSlider 滑块 v-model 双向：拖动后 form.alpha 更新，提交 payload 携带 alpha_dev", async () => {
    const w = await gotoStep2();
    const radios = w.findAll('input[type="radio"][name="project_type"]');
    const devOps = radios.find((r) => (r.element as HTMLInputElement).value === "dev_and_ops")!;
    await devOps.setValue();
    await flushPromises();

    const range = w.find('input[type="range"]');
    expect(range.exists()).toBe(true);
    await range.setValue(0.8);
    await flushPromises();

    // 进入 step 7 提交，检查 payload
    for (let i = 0; i < 5; i++) {
      await w.find("[data-test='wizard-next']").trigger("click");
    }
    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();

    const payload = (projectsApi.create as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(payload.alpha_dev).toBeCloseTo(0.8, 5);
    expect(payload.project_type).toBe("dev_and_ops");
  });
});
