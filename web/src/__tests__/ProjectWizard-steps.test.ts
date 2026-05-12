import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ProjectWizard from "@/views/ProjectWizard.vue";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    create: vi.fn(),
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
