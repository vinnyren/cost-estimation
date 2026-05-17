import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import AllocatorPanel from "@/components/result/AllocatorPanel.vue";
import type { FunctionPoint } from "@/api/functions";

vi.mock("@/api/calc", () => ({
  calcApi: {
    allocate: vi.fn(),
  },
}));

vi.mock("@/api/functions", () => ({
  functionsApi: {
    list: vi.fn(),
    patch: vi.fn(),
    create: vi.fn(),
    remove: vi.fn(),
    bulk: vi.fn(),
    snapshots: vi.fn(),
    restore: vi.fn(),
  },
}));

import { calcApi } from "@/api/calc";
import { functionsApi } from "@/api/functions";

const mockFn = <T>(impl: T) => impl as ReturnType<typeof vi.fn>;

function fp(over: Partial<FunctionPoint>): FunctionPoint {
  return {
    id: "fp-x",
    project_id: "p-1",
    category: "EI",
    complexity: "low",
    fp_kind: "dev",
    ufp: 3,
    us: 3,
    source: "manual",
    version: 1,
    ...over,
  };
}

// 两个 dev 模块（财务管理 2 条、电子结算 1 条）+ 一个 ops 模块
const FPS: FunctionPoint[] = [
  fp({ id: "d1", l1_module: "财务管理", fp_kind: "dev", us: 30 }),
  fp({ id: "d2", l1_module: "财务管理", fp_kind: "dev", us: 10 }),
  fp({ id: "d3", l1_module: "电子结算", fp_kind: "dev", us: 20 }),
  fp({ id: "o1", l1_module: "运维支持", fp_kind: "ops", us: 5 }),
];

const stubReverseResult = {
  budget_for_dev: 1000000,
  budget_for_ops: 200000,
  scale_adjusted_bands: { P10: 360, P50: 300, P90: 250 },
  scale_unadjusted_bands: { P10: 297, P50: 275, P90: 252 },
  scale_adjusted_ops_bands: { P10: 60, P50: 50, P90: 40 },
  scale_unadjusted_ops_bands: { P10: 55, P50: 45, P90: 35 },
  cf_used: 1.21,
  recommended_band: "P50" as const,
};

const allocateResult = {
  items: [
    { name: "财务管理", us: 200, locked: false, audit_tag: "budget_derived" },
    { name: "电子结算", us: 100, locked: false, audit_tag: "budget_derived" },
  ],
  validation: { recalc_total_us: 300, recalc_total_adjusted: 363, error_pct: 0.2 },
};

function mountPanel() {
  return mount(AllocatorPanel, {
    props: { reverseResult: stubReverseResult, projectId: "p-1" },
  });
}

describe("AllocatorPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFn(functionsApi.list).mockResolvedValue(FPS);
    mockFn(functionsApi.patch).mockResolvedValue(fp({}));
    mockFn(calcApi.allocate).mockResolvedValue(allocateResult);
  });

  it("drafts 从真实 FP 的一级模块生成（dev 口径 2 个模块）", async () => {
    const w = mountPanel();
    await flushPromises();
    const rows = w.findAll(".allocator-drafts tbody tr");
    expect(rows).toHaveLength(2);
    expect(w.text()).toContain("财务管理");
    expect(w.text()).toContain("电子结算");
    // weight 初值 = 该模块现有 US 总和
    const firstWeight = w.find(
      ".allocator-drafts tbody tr input.field-input",
    ).element as HTMLInputElement;
    expect(Number(firstWeight.value)).toBe(40); // 财务管理 30 + 10
  });

  it("切换到运维口径后重新分组（1 个 ops 模块）", async () => {
    const w = mountPanel();
    await flushPromises();
    const opsBtn = w.findAll(".kind-toggle button")[1];
    await opsBtn.trigger("click");
    await flushPromises();
    const rows = w.findAll(".allocator-drafts tbody tr");
    expect(rows).toHaveLength(1);
    expect(w.text()).toContain("运维支持");
  });

  it("生成分摊调 calcApi.allocate（dev 用 scale_adjusted_bands 推荐档）", async () => {
    const w = mountPanel();
    await flushPromises();
    await w.find(".allocator-actions .btn-primary").trigger("click");
    await flushPromises();
    expect(calcApi.allocate).toHaveBeenCalledOnce();
    const arg = mockFn(calcApi.allocate).mock.calls[0][0];
    expect(arg.target_us).toBe(300); // scale_adjusted_bands.P50
    expect(arg.drafts.map((d: { name: string }) => d.name)).toEqual([
      "财务管理",
      "电子结算",
    ]);
    expect(w.emitted("allocated")).toBeTruthy();
  });

  it("写回按各 FP 现有 US 占比 PATCH 功能点", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const w = mountPanel();
    await flushPromises();
    await w.find(".allocator-actions .btn-primary").trigger("click");
    await flushPromises();

    // 找到写回按钮（分摊结果区里的 .btn 非 primary）
    const writeBtn = w
      .findAll("button")
      .find((b) => b.text().includes("写回 FP 表"));
    expect(writeBtn).toBeTruthy();
    await writeBtn!.trigger("click");
    await flushPromises();

    // 财务管理 200 → d1 占 30/40=0.75 → 150 ; d2 占 10/40 → 50
    // 电子结算 100 → d3 唯一 → 100
    expect(functionsApi.patch).toHaveBeenCalledTimes(3);
    const calls = mockFn(functionsApi.patch).mock.calls;
    const byId: Record<string, number> = {};
    for (const c of calls) byId[c[1] as string] = (c[2] as { us: number }).us;
    expect(byId["d1"]).toBeCloseTo(150);
    expect(byId["d2"]).toBeCloseTo(50);
    expect(byId["d3"]).toBeCloseTo(100);
    expect(w.emitted("fp-updated")).toBeTruthy();
    expect(w.emitted("fp-updated")?.[0][0]).toBe(3);
    confirmSpy.mockRestore();
  });

  it("运维口径无 FP 时显示提示且不渲染分摊表", async () => {
    mockFn(functionsApi.list).mockResolvedValue([
      fp({ id: "d1", l1_module: "财务管理", fp_kind: "dev", us: 30 }),
    ]);
    const w = mountPanel();
    await flushPromises();
    await w.findAll(".kind-toggle button")[1].trigger("click");
    await flushPromises();
    expect(w.text()).toContain("当前口径暂无功能点");
    expect(w.findAll(".allocator-drafts")).toHaveLength(0);
  });
});
