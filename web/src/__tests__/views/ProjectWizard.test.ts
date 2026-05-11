import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ProjectWizard from "@/views/ProjectWizard.vue";
import { projectsApi } from "@/api/projects";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    create: vi.fn(),
  },
}));

vi.mock("@/api/params", () => ({
  paramsApi: {
    effective: vi.fn().mockResolvedValue({
      cf: { budget: 1.5, bidding: 1.21, planning: 1.1, change: 1.05, settled: 1.0 },
    }),
    global: vi.fn().mockResolvedValue({
      cf: { budget: 1.5, bidding: 1.21, planning: 1.1, change: 1.05, settled: 1.0 },
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

const mountWizard = () =>
  mount(ProjectWizard, {
    global: { plugins: [createPinia(), router] },
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

  // TODO(T17-T18): factors_dev / factors_ops / 确认页 UI 落地后再补对应端到端用例。
});

/**
 * NOTE (T16 — Wizard step 4 正/反向):
 *   Step 4 落地：mode radio 二选一 / reverse 时显示 target_total / target_total=0
 *   时禁止前进 / reverse + target_total 提交时映射到 payload.target_cost。
 */

describe("Wizard step 4 — mode + target_total (T16)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    (projectsApi.create as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "p-99",
      name: "new",
      project_type: "dev_only",
      mode: "reverse",
      city: "北京",
      industry: "电子政务",
      phase: "bidding",
      basis_data_ver: "CSBMK®-202510",
      created_at: "",
      updated_at: "",
    });
  });

  async function gotoStep4() {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("项目甲");
    await w.find("[data-test='wizard-next']").trigger("click"); // → step 2
    await w.find("[data-test='wizard-next']").trigger("click"); // → step 3
    await w.find("[data-test='wizard-next']").trigger("click"); // → step 4
    await flushPromises();
    return w;
  }

  it("渲染 forward + reverse radio 两个选项", async () => {
    const w = await gotoStep4();
    const radios = w.findAll('input[type="radio"][name="mode"]');
    expect(radios.length).toBe(2);
    const values = radios.map((r) => (r.element as HTMLInputElement).value);
    expect(values).toContain("forward");
    expect(values).toContain("reverse");
    expect(w.text()).toContain("正向");
    expect(w.text()).toContain("反向");
  });

  it("默认 forward 模式：target_total 输入框不显示", async () => {
    const w = await gotoStep4();
    expect(w.find('input[name="target_total"]').exists()).toBe(false);
  });

  it("切到 reverse 模式：target_total number input 出现", async () => {
    const w = await gotoStep4();
    const radios = w.findAll('input[type="radio"][name="mode"]');
    const reverseRadio = radios.find(
      (r) => (r.element as HTMLInputElement).value === "reverse",
    )!;
    await reverseRadio.setValue();
    await flushPromises();

    const targetInput = w.find('input[name="target_total"]');
    expect(targetInput.exists()).toBe(true);
    expect((targetInput.element as HTMLInputElement).type).toBe("number");
  });

  it("reverse + target_total=0 时下一步按钮 disabled", async () => {
    const w = await gotoStep4();
    const radios = w.findAll('input[type="radio"][name="mode"]');
    const reverseRadio = radios.find(
      (r) => (r.element as HTMLInputElement).value === "reverse",
    )!;
    await reverseRadio.setValue();
    await flushPromises();

    // target_total 默认值是 0
    const nextBtn = w.find("[data-test='wizard-next']");
    expect((nextBtn.element as HTMLButtonElement).disabled).toBe(true);
  });

  it("reverse + target_total>0 时下一步按钮启用", async () => {
    const w = await gotoStep4();
    const radios = w.findAll('input[type="radio"][name="mode"]');
    const reverseRadio = radios.find(
      (r) => (r.element as HTMLInputElement).value === "reverse",
    )!;
    await reverseRadio.setValue();
    await flushPromises();

    await w.find('input[name="target_total"]').setValue(10000);
    await flushPromises();

    const nextBtn = w.find("[data-test='wizard-next']");
    expect((nextBtn.element as HTMLButtonElement).disabled).toBe(false);
  });

  it("reverse 模式 submit：payload.target_cost 映射 target_total", async () => {
    const w = await gotoStep4();
    const radios = w.findAll('input[type="radio"][name="mode"]');
    const reverseRadio = radios.find(
      (r) => (r.element as HTMLInputElement).value === "reverse",
    )!;
    await reverseRadio.setValue();
    await flushPromises();

    await w.find('input[name="target_total"]').setValue(10000);
    await flushPromises();

    // step 4 → 5 → 6 → 7
    for (let i = 0; i < 3; i++) {
      await w.find("[data-test='wizard-next']").trigger("click");
    }

    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    expect(submitBtn).toBeDefined();
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();

    const payload = (projectsApi.create as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(payload.mode).toBe("reverse");
    expect(payload.target_cost).toBe(10000);
  });
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
    // dev_only 模式下 step 7 不展示 α 行（只在 dev_and_ops 显示）。
    // 通过 submit payload 验证 alpha_dev 回到 1.0。
    const submitBtn = w.findAll("button").find((b) =>
      b.text().includes("创建项目"),
    );
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();
    const payload = (projectsApi.create as unknown as ReturnType<typeof vi.fn>)
      .mock.calls[0][0];
    expect(payload.alpha_dev).toBeCloseTo(1.0, 5);
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

/**
 * NOTE (T15 — Wizard step 3 项目阶段 + CF 预览):
 *   Step 3 落地：PhaseCfPreview 渲染 5 个阶段卡片，每张显示对应的 CF。
 *   切换阶段 → form.phase 同步更新；最终 payload.phase 反映用户选择。
 */

describe("Wizard step 3 — phase + CF preview (T15)", () => {
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

  async function gotoStep3() {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("项目甲");
    await w.find("[data-test='wizard-next']").trigger("click"); // → step 2
    await w.find("[data-test='wizard-next']").trigger("click"); // → step 3
    await flushPromises();
    return w;
  }

  it("renders 5 phase options with CF values from effective", async () => {
    const w = await gotoStep3();
    const cards = w.findAll('[data-testid^="phase-card-"]');
    expect(cards.length).toBe(5);

    // 每个 phase card 应展示其 CF 数值（来自 mock 的 effective.cf）
    const expectedCf: Record<string, string> = {
      budget: "1.50",
      bidding: "1.21",
      planning: "1.10",
      change: "1.05",
      settled: "1.00",
    };
    for (const [key, val] of Object.entries(expectedCf)) {
      const card = w.find(`[data-testid="phase-card-${key}"]`);
      expect(card.exists()).toBe(true);
      expect(card.text()).toContain(`CF = ${val}`);
    }
  });

  it("clicking a phase card updates form.phase", async () => {
    const w = await gotoStep3();

    // 默认 bidding
    const biddingCard = w.find('[data-testid="phase-card-bidding"]');
    expect(biddingCard.attributes("data-active")).toBe("true");

    // 切到 budget
    const budgetRadio = w.find('[data-testid="phase-card-budget"] input[type="radio"]');
    await budgetRadio.trigger("change");
    await flushPromises();

    expect(w.find('[data-testid="phase-card-budget"]').attributes("data-active")).toBe("true");
    expect(w.find('[data-testid="phase-card-bidding"]').attributes("data-active")).toBe("false");

    // 跳到 step 7 检查 form.phase 写入（确认页"阶段"行显示 budget）。
    for (let i = 0; i < 4; i++) {
      await w.find("[data-test='wizard-next']").trigger("click");
    }
    const summary = w.find('[data-testid="confirm-summary"]');
    expect(summary.exists()).toBe(true);
    expect(summary.text()).toContain("budget");
  });

  it("CF 默认 1.00 when key missing from effective", async () => {
    // 临时覆盖 mock 返回空 cf
    const { paramsApi } = await import("@/api/params");
    (paramsApi.global as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ cf: {} });

    const w = await gotoStep3();
    const biddingCard = w.find('[data-testid="phase-card-bidding"]');
    expect(biddingCard.text()).toContain("CF = 1.00");
  });
});

/**
 * NOTE (T17 — Wizard step 5/6 factor dropdowns + 实时 chain 预览):
 *   Step 5：渲染 effective.factors_dev 中的每个因子为 FactorDropdown，
 *           底部展示 devFactorPreview（链式乘积，默认 1.00）。
 *   Step 6：当 include_ops 为 true 渲染 factors_ops，否则展示 skip 提示。
 *   切换 dropdown → 预览即时更新。
 */

describe("Wizard step 5/6 — factor dropdowns (T17)", () => {
  beforeEach(async () => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    const { paramsApi } = await import("@/api/params");
    (paramsApi.global as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      cf: { budget: 1.5, bidding: 1.21, planning: 1.1, change: 1.05, settled: 1.0 },
      factors_dev: {
        app_type: { OLTP: 1.0, OLAP: 1.1 },
        platform: { web: 1.0, mobile: 1.2 },
      },
      factors_ops: {
        update_freq: { low: 0.8, high: 1.3 },
      },
    });
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

  async function gotoStep5() {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("项目甲");
    await flushPromises();
    // step 1 → 2 → 3 → 4 → 5
    for (let i = 0; i < 4; i++) {
      await w.find("[data-test='wizard-next']").trigger("click");
    }
    await flushPromises();
    return w;
  }

  it("step 5：每个 factors_dev 因子渲染一个 dropdown", async () => {
    const w = await gotoStep5();
    expect(w.text()).toContain("开发调整因子");
    const selects = w.findAll("select");
    // 城市 / 行业（step 1 已隐藏 — 现在 currentStep=5）
    // step 5 中只剩下 factor dropdown
    expect(selects.length).toBeGreaterThanOrEqual(2);
    // 两个因子键 app_type / platform 都应该出现在 data-factor 属性
    expect(w.find('[data-factor="app_type"]').exists()).toBe(true);
    expect(w.find('[data-factor="platform"]').exists()).toBe(true);
  });

  it("step 5：初始 dev_factor preview 为 1.00", async () => {
    const w = await gotoStep5();
    const preview = w.find('[data-testid="dev-factor-preview"]');
    expect(preview.exists()).toBe(true);
    expect(preview.text()).toContain("1.00");
  });

  it("step 5：选择 OLAP → preview 更新为 1.10", async () => {
    const w = await gotoStep5();
    const appTypeSelect = w.find('[data-factor="app_type"] select');
    await appTypeSelect.setValue("OLAP");
    await flushPromises();
    const preview = w.find('[data-testid="dev-factor-preview"]');
    expect(preview.text()).toContain("1.10");
  });

  it("step 5：多因子链相乘（OLAP × mobile = 1.32）", async () => {
    const w = await gotoStep5();
    await w.find('[data-factor="app_type"] select').setValue("OLAP");
    await w.find('[data-factor="platform"] select').setValue("mobile");
    await flushPromises();
    const preview = w.find('[data-testid="dev-factor-preview"]');
    // 1.1 * 1.2 = 1.32
    expect(preview.text()).toContain("1.32");
  });

  it("step 6 with include_ops=false：显示跳过提示", async () => {
    const w = await gotoStep5();
    // 默认 dev_only → include_ops=false
    await w.find("[data-test='wizard-next']").trigger("click");
    await flushPromises();
    const skip = w.find('[data-testid="ops-skip"]');
    expect(skip.exists()).toBe(true);
    expect(skip.text()).toContain("未启用运维");
  });

  it("step 6 with include_ops=true：渲染 ops 因子 dropdown 与预览", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("混合项目");
    await w.find("[data-test='wizard-next']").trigger("click"); // → step 2
    // 切到 dev_and_ops → include_ops=true
    const radios = w.findAll('input[type="radio"][name="project_type"]');
    const devOps = radios.find(
      (r) => (r.element as HTMLInputElement).value === "dev_and_ops",
    )!;
    await devOps.setValue();
    await flushPromises();
    // step 2 → 3 → 4 → 5 → 6
    for (let i = 0; i < 4; i++) {
      await w.find("[data-test='wizard-next']").trigger("click");
    }
    await flushPromises();

    expect(w.text()).toContain("运维调整因子");
    expect(w.find('[data-factor="update_freq"]').exists()).toBe(true);
    const opsPreview = w.find('[data-testid="ops-factor-preview"]');
    expect(opsPreview.exists()).toBe(true);
    expect(opsPreview.text()).toContain("1.00");

    // 选 low (0.8) → preview 0.80
    await w.find('[data-factor="update_freq"] select').setValue("low");
    await flushPromises();
    expect(w.find('[data-testid="ops-factor-preview"]').text()).toContain("0.80");
  });

  it("step 5：dropdown 选项展示 ×multiplier 格式", async () => {
    const w = await gotoStep5();
    const appTypeSelect = w.find('[data-factor="app_type"] select');
    const html = appTypeSelect.html();
    expect(html).toContain("×1.00");
    expect(html).toContain("×1.10");
  });
});

/**
 * NOTE (T18 — Wizard step 7 确认 + 提交):
 *   Step 7 展示全部参数（dl 列表），submit() 把 v2.0 新字段
 *   （client / evaluator / include_ops / factors_dev / factors_ops）
 *   都写进 create payload。空因子组 → factors_* = undefined（不发送）。
 *   factors_ops 仅在 include_ops=true 时携带。
 */
describe("Wizard step 7 — 确认 + 提交 (T18)", () => {
  beforeEach(async () => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    const { paramsApi } = await import("@/api/params");
    (paramsApi.global as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      cf: { budget: 1.5, bidding: 1.21, planning: 1.1, change: 1.05, settled: 1.0 },
      factors_dev: {
        app_type: { OLTP: 1.0, OLAP: 1.1 },
        platform: { web: 1.0, mobile: 1.2 },
      },
      factors_ops: {
        update_freq: { low: 0.8, high: 1.3 },
      },
    });
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

  async function advanceToStep7(w: ReturnType<typeof mountWizard>) {
    for (let i = 0; i < 6; i++) {
      await w.find("[data-test='wizard-next']").trigger("click");
      await flushPromises();
    }
  }

  it("step 7 渲染 confirm-summary dl 包含项目名、城市、客户/评估方", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("项目甲");
    await w.find('input[name="client"]').setValue("甲方公司");
    await w.find('input[name="evaluator"]').setValue("第三方评估");
    await flushPromises();
    await advanceToStep7(w);

    const summary = w.find('[data-testid="confirm-summary"]');
    expect(summary.exists()).toBe(true);
    const text = summary.text();
    expect(text).toContain("项目甲");
    expect(text).toContain("北京");
    expect(text).toContain("电子政务");
    expect(text).toContain("甲方公司");
    expect(text).toContain("第三方评估");
    expect(text).toContain("仅开发");
    expect(text).toContain("bidding");
    expect(text).toContain("正向");
  });

  it("空 client / evaluator 显示占位符 —", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("无客户项目");
    await flushPromises();
    await advanceToStep7(w);

    const summary = w.find('[data-testid="confirm-summary"]');
    expect(summary.text()).toContain("— / —");
  });

  it("submit payload 携带 client + evaluator", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("项目甲");
    await w.find('input[name="client"]').setValue("甲方");
    await w.find('input[name="evaluator"]').setValue("评估方");
    await flushPromises();
    await advanceToStep7(w);

    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();

    const payload = (projectsApi.create as unknown as ReturnType<typeof vi.fn>)
      .mock.calls[0][0];
    expect(payload.client).toBe("甲方");
    expect(payload.evaluator).toBe("评估方");
  });

  it("submit payload 携带 factors_dev 当至少一个因子被选中", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("带因子项目");
    await flushPromises();
    // 进到 step 5（开发因子）
    for (let i = 0; i < 4; i++) {
      await w.find("[data-test='wizard-next']").trigger("click");
      await flushPromises();
    }
    await w.find('[data-factor="app_type"] select').setValue("OLAP");
    await flushPromises();
    // step 5 → 6 → 7
    for (let i = 0; i < 2; i++) {
      await w.find("[data-test='wizard-next']").trigger("click");
      await flushPromises();
    }

    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();

    const payload = (projectsApi.create as unknown as ReturnType<typeof vi.fn>)
      .mock.calls[0][0];
    expect(payload.factors_dev).toBeDefined();
    expect(payload.factors_dev.app_type).toBe("OLAP");
  });

  it("submit payload factors_dev=undefined 当没有任何选择", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("空因子项目");
    await flushPromises();
    await advanceToStep7(w);

    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();

    const payload = (projectsApi.create as unknown as ReturnType<typeof vi.fn>)
      .mock.calls[0][0];
    expect(payload.factors_dev).toBeUndefined();
  });

  it("dev_only 项目：submit payload.factors_ops = undefined（即使 ops 因子有值也被丢弃）", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("仅开发");
    await flushPromises();
    // dev_only 默认 → include_ops=false → step 6 是 skip
    await advanceToStep7(w);

    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();

    const payload = (projectsApi.create as unknown as ReturnType<typeof vi.fn>)
      .mock.calls[0][0];
    expect(payload.include_ops).toBe(false);
    expect(payload.factors_ops).toBeUndefined();
  });

  it("dev_and_ops + ops 因子选中：payload.factors_ops 携带选择", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("混合项目");
    await w.find("[data-test='wizard-next']").trigger("click"); // → step 2
    const radios = w.findAll('input[type="radio"][name="project_type"]');
    const devOps = radios.find(
      (r) => (r.element as HTMLInputElement).value === "dev_and_ops",
    )!;
    await devOps.setValue();
    await flushPromises();
    // step 2 → 3 → 4 → 5 → 6
    for (let i = 0; i < 4; i++) {
      await w.find("[data-test='wizard-next']").trigger("click");
      await flushPromises();
    }
    // step 6: 选 update_freq=low
    await w.find('[data-factor="update_freq"] select').setValue("low");
    await flushPromises();
    // step 6 → 7
    await w.find("[data-test='wizard-next']").trigger("click");
    await flushPromises();

    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();

    const payload = (projectsApi.create as unknown as ReturnType<typeof vi.fn>)
      .mock.calls[0][0];
    expect(payload.include_ops).toBe(true);
    expect(payload.factors_ops).toBeDefined();
    expect(payload.factors_ops.update_freq).toBe("low");
  });

  it("step 7 显示 α 行仅当 dev_and_ops", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("混合项目");
    await w.find("[data-test='wizard-next']").trigger("click"); // → step 2
    const radios = w.findAll('input[type="radio"][name="project_type"]');
    const devOps = radios.find(
      (r) => (r.element as HTMLInputElement).value === "dev_and_ops",
    )!;
    await devOps.setValue();
    await flushPromises();
    // step 2 → 3 → 4 → 5 → 6 → 7
    for (let i = 0; i < 5; i++) {
      await w.find("[data-test='wizard-next']").trigger("click");
      await flushPromises();
    }
    const summary = w.find('[data-testid="confirm-summary"]');
    expect(summary.text()).toContain("α");
    expect(summary.text()).toContain("开发 + 运维");
  });

  it("payload 始终携带 basis_data_ver = CSBMK®-202510", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.find('input[name="name"]').setValue("基础数据版本测试");
    await flushPromises();
    await advanceToStep7(w);

    const submitBtn = w.findAll("button").find((b) => b.text().includes("创建项目"));
    await submitBtn!.trigger("click");
    await flushPromises();
    await flushPromises();

    const payload = (projectsApi.create as unknown as ReturnType<typeof vi.fn>)
      .mock.calls[0][0];
    expect(payload.basis_data_ver).toBe("CSBMK®-202510");
  });
});
