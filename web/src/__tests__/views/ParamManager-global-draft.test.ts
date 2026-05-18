import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ParamManager from "@/views/ParamManager.vue";
import { paramsApi } from "@/api/params";

vi.mock("@/api/params", () => ({
  paramsApi: {
    effective: vi.fn(),
    global: vi.fn(),
    override: vi.fn(),
    patchGlobal: vi.fn().mockResolvedValue({ updated: "x" }),
    resetGlobal: vi.fn(),
  },
}));
vi.mock("@/api/snapshots", () => ({
  snapshotsApi: { list: vi.fn().mockResolvedValue([]) },
}));

const globalEff = {
  cf: { bidding: 1.21 },
  productivity_dev: { 电子政务: { P10: 2.04, P50: 6.41, P90: 15.36 } },
  productivity_ops: {},
  city_rate: { 北京: { dev: 32198, ops: 26335, class: "A" } },
  factors_dev: {},
  factors_ops: {},
  hours_per_pm: 174,
  ops_cost_ratio: { P50: 0.0902 },
  overrides: {},
};

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: "/parameters", component: ParamManager, name: "global-params" }],
});

function mountGlobal() {
  return mount(ParamManager, {
    props: { projectId: null },
    global: { plugins: [createPinia(), router] },
  });
}

describe("ParamManager — 全局草稿编辑", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    (paramsApi.global as ReturnType<typeof vi.fn>).mockResolvedValue(globalEff);
    (paramsApi.resetGlobal as ReturnType<typeof vi.fn>).mockResolvedValue(globalEff);
  });

  it("全局模式改 OverrideField → 不即时落库，写入草稿", async () => {
    const w = mountGlobal();
    await flushPromises();
    const input = w.find("input[type='number']");
    await input.setValue(40000);
    await flushPromises();
    expect(paramsApi.patchGlobal).not.toHaveBeenCalled();
    expect(w.find("[data-testid='draft-dirty']").exists()).toBe(true);
  });

  it("点保存 → 逐 leaf 调 patchGlobal", async () => {
    const w = mountGlobal();
    await flushPromises();
    const input = w.find("input[type='number']");
    await input.setValue(40000);
    await flushPromises();
    await w.find("[data-testid='draft-save']").trigger("click");
    await flushPromises();
    expect(paramsApi.patchGlobal).toHaveBeenCalledWith("city_rate.北京.dev", 40000);
  });

  it("点撤销 → 丢弃草稿，dirty 提示消失", async () => {
    const w = mountGlobal();
    await flushPromises();
    await w.find("input[type='number']").setValue(40000);
    await flushPromises();
    await w.find("[data-testid='draft-undo']").trigger("click");
    await flushPromises();
    expect(w.find("[data-testid='draft-dirty']").exists()).toBe(false);
  });

  it("点还原出厂 → 二次确认后调 resetGlobal", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const w = mountGlobal();
    await flushPromises();
    await w.find("[data-testid='draft-reset']").trigger("click");
    await flushPromises();
    expect(paramsApi.resetGlobal).toHaveBeenCalled();
  });

  it("还原出厂 — 用户取消确认 → 不调 resetGlobal", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const w = mountGlobal();
    await flushPromises();
    await w.find("[data-testid='draft-reset']").trigger("click");
    await flushPromises();
    expect(paramsApi.resetGlobal).not.toHaveBeenCalled();
  });
});
