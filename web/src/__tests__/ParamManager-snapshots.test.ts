// v2.0 T12 — ParamManager 快照 tab 实装 (GAP-H)
//
// Snapshots tab 应接通后端 /api/params/snapshots 4 个 endpoint：
//   list / create / restore / remove
// 切换到 snapshots tab 时 list；点击「立即快照」create；
// 「恢复」restore 后重新 loadFor；「删除」remove 后 reload。
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
import ParamManager from "@/views/ParamManager.vue";
import { paramsApi } from "@/api/params";
import { snapshotsApi } from "@/api/snapshots";

vi.mock("@/api/params", () => ({
  paramsApi: {
    effective: vi.fn(),
    override: vi.fn(),
  },
}));

vi.mock("@/api/snapshots", () => ({
  snapshotsApi: {
    list: vi.fn(),
    create: vi.fn(),
    restore: vi.fn(),
    remove: vi.fn(),
  },
}));

const baseEffective = {
  cf: { budget: 1.39, bidding: 1.21, planning: 1.10, change: 1.10, settled: 1.00 },
  productivity_dev: { 电子政务: { P10: 2.04, P50: 6.41, P90: 15.36 } },
  productivity_ops: {},
  city_rate: { 北京: { dev: 32198, ops: 26335, class: "A" } },
  factors_dev: {},
  factors_ops: {},
  hours_per_pm: 174,
  ops_cost_ratio: { P50: 0.0902 },
  overrides: {},
};

const mockSnaps = [
  { id: 1, scope: "global", label: "实验前", created_at: "2026-05-11T00:00:00Z" },
  { id: 2, scope: "global", label: "after-edit", created_at: "2026-05-11T01:00:00Z" },
];

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: "/projects/:id/parameters", component: ParamManager, name: "param-manager" }],
});

describe("ParamManager — 快照 tab (GAP-H)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    (paramsApi.effective as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(baseEffective);
    (snapshotsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockSnaps);
    (snapshotsApi.create as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 3,
      scope: "global",
      label: "x",
      created_at: "2026-05-11T02:00:00Z",
    });
    (snapshotsApi.restore as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({});
    (snapshotsApi.remove as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
  });

  it("切到 snapshots tab → 调 snapshotsApi.list 并渲染快照行", async () => {
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();

    const tabs = w.findAll("[role='tab']");
    const snapTab = tabs.find((t) => t.text().includes("快照"))!;
    expect(snapTab).toBeTruthy();
    await snapTab.trigger("click");
    await flushPromises();

    expect(snapshotsApi.list).toHaveBeenCalledWith("global");
    expect(w.text()).toContain("实验前");
    expect(w.text()).toContain("after-edit");
  });

  it("点击「立即快照」→ 调 create({scope:'global', label}) 后 reload", async () => {
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();

    const tabs = w.findAll("[role='tab']");
    const snapTab = tabs.find((t) => t.text().includes("快照"))!;
    await snapTab.trigger("click");
    await flushPromises();

    const input = w.find<HTMLInputElement>(".snap-label-input");
    expect(input.exists()).toBe(true);
    await input.setValue("ckpt-1");
    const btn = w.findAll("button").find((b) => b.text().includes("立即快照"))!;
    await btn.trigger("click");
    await flushPromises();

    expect(snapshotsApi.create).toHaveBeenCalledWith({
      scope: "global",
      label: "ckpt-1",
    });
    // 创建后 reload — list 至少被调 2 次（mount 切到 tab 1 次 + create 后 1 次）
    expect((snapshotsApi.list as unknown as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("点击「恢复」+ 确认 → 调 restore(id) 后重新 loadFor + reload", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();

    const tabs = w.findAll("[role='tab']");
    const snapTab = tabs.find((t) => t.text().includes("快照"))!;
    await snapTab.trigger("click");
    await flushPromises();

    const restoreBtn = w.findAll("button").find((b) => b.text() === "恢复")!;
    expect(restoreBtn).toBeTruthy();
    await restoreBtn.trigger("click");
    await flushPromises();

    expect(confirmSpy).toHaveBeenCalled();
    expect(snapshotsApi.restore).toHaveBeenCalledWith(1);
    // 恢复后重新加载 effective
    expect((paramsApi.effective as unknown as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThanOrEqual(2);
    confirmSpy.mockRestore();
  });

  it("点击「删除」+ 确认 → 调 remove(id) 后 reload", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();

    const tabs = w.findAll("[role='tab']");
    const snapTab = tabs.find((t) => t.text().includes("快照"))!;
    await snapTab.trigger("click");
    await flushPromises();

    const deleteBtn = w.findAll("button").find((b) => b.text() === "删除")!;
    expect(deleteBtn).toBeTruthy();
    await deleteBtn.trigger("click");
    await flushPromises();

    expect(confirmSpy).toHaveBeenCalled();
    expect(snapshotsApi.remove).toHaveBeenCalledWith(1);
    expect((snapshotsApi.list as unknown as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThanOrEqual(2);
    confirmSpy.mockRestore();
  });

  it("点击「恢复」+ 取消 → 不调 restore", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();

    const tabs = w.findAll("[role='tab']");
    const snapTab = tabs.find((t) => t.text().includes("快照"))!;
    await snapTab.trigger("click");
    await flushPromises();

    const restoreBtn = w.findAll("button").find((b) => b.text() === "恢复")!;
    await restoreBtn.trigger("click");
    await flushPromises();

    expect(snapshotsApi.restore).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("无快照时显示「暂无快照」", async () => {
    (snapshotsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    router.push("/projects/1/parameters");
    await router.isReady();
    const w = mount(ParamManager, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();

    const tabs = w.findAll("[role='tab']");
    const snapTab = tabs.find((t) => t.text().includes("快照"))!;
    await snapTab.trigger("click");
    await flushPromises();

    expect(w.text()).toContain("暂无快照");
  });
});
