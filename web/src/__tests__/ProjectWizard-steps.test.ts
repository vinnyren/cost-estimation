import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ProjectWizard from "@/views/ProjectWizard.vue";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    create: vi.fn().mockResolvedValue({ id: "new-proj-1" }),
    get: vi.fn().mockResolvedValue(null),
    update: vi.fn(),
  },
}));

vi.mock("@/api/params", () => ({
  paramsApi: {
    effective: vi.fn().mockResolvedValue({ cf: { bidding: 1.21 } }),
    global: vi.fn().mockResolvedValue({ cf: { bidding: 1.21 } }),
  },
}));

vi.mock("@/api/factorMeta", () => ({
  factorMetaApi: { get: vi.fn().mockResolvedValue({ factors_dev: {}, factors_ops: {} }) },
}));

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: "/projects/new", component: ProjectWizard, name: "project-wizard" },
    {
      path: "/projects/:id/functions",
      name: "fp-editor",
      component: { template: "<div/>" },
    },
  ],
});

const mountWizard = () =>
  mount(ProjectWizard, {
    global: { plugins: [createPinia(), router] },
  });

describe("ProjectWizard 7 steps", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("renders 7 step indicators", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.vm.$nextTick();
    const steps = w.findAll('[data-testid="wizard-step"]');
    expect(steps.length).toBe(7);
  });

  it("step 1 has client + evaluator inputs", async () => {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await w.vm.$nextTick();
    expect(w.find('input[name="client"]').exists()).toBe(true);
    expect(w.find('input[name="evaluator"]').exists()).toBe(true);
  });
});

describe("ProjectWizard assessment_kind field", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  async function goToStep2() {
    router.push("/projects/new");
    await router.isReady();
    const w = mountWizard();
    await flushPromises();
    // Fill in name so step 1 gate passes, then advance to step 2
    await w.find('input[name="name"]').setValue("测试项目");
    await w.find('[data-test="wizard-next"]').trigger("click");
    await w.vm.$nextTick();
    return w;
  }

  it("step 2 renders assessment_kind field with both radio options", async () => {
    const w = await goToStep2();
    const container = w.find('[data-testid="wizard-assessment-kind"]');
    expect(container.exists()).toBe(true);
    const radios = container.findAll('input[type="radio"][name="assessment_kind"]');
    expect(radios).toHaveLength(2);
    const values = radios.map((r) => r.element.getAttribute("value"));
    expect(values).toContain("development");
    expect(values).toContain("enhancement");
  });

  it("assessment_kind defaults to 'development'", async () => {
    const w = await goToStep2();
    const devRadio = w.find('input[type="radio"][name="assessment_kind"][value="development"]');
    expect((devRadio.element as HTMLInputElement).checked).toBe(true);
  });

  it("selecting 增强项目 sets assessment_kind to 'enhancement' in create payload", async () => {
    const { projectsApi } = await import("@/api/projects");
    const w = await goToStep2();

    // Select enhancement
    const enhancementRadio = w.find(
      'input[type="radio"][name="assessment_kind"][value="enhancement"]',
    );
    await enhancementRadio.trigger("change");
    await w.vm.$nextTick();

    // Advance through steps 3–6 to reach confirmation (step 7), then submit
    for (let step = 2; step < 7; step++) {
      const nextBtn = w.find('[data-test="wizard-next"]');
      if (nextBtn.exists()) {
        await nextBtn.trigger("click");
        await w.vm.$nextTick();
      }
    }

    // Now on step 7 — submit
    await w.find(".btn.btn-primary").trigger("click");
    await flushPromises();

    expect(projectsApi.create).toHaveBeenCalledWith(
      expect.objectContaining({ assessment_kind: "enhancement" }),
    );
  });
});
