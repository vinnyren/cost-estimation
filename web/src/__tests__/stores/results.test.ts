import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useResultsStore } from "@/stores/results";
import type { ForwardResult, ReverseResult } from "@/api/calc";

const sampleForward = (): ForwardResult => ({
  scale_us: 275,
  scale_adjusted: 332.75,
  cf_used: 1.21,
  effort_dev_hours: { P10: 800, P50: 1600, P90: 2400 },
  effort_ops_hours: { P10: 0, P50: 0, P90: 0 },
  cost_dev_yuan: { P10: 300000, P50: 489180, P90: 700000 },
  cost_ops_yuan: { P10: 0, P50: 0, P90: 0 },
  cost_other_yuan: 0,
  cost_total_yuan: { P10: 300000, P50: 489180, P90: 700000 },
});

const sampleReverse = (): ReverseResult => ({
  budget_for_dev: 1_000_000,
  budget_for_ops: 0,
  scale_adjusted_bands: { P10: 300, P50: 200, P90: 100 },
  scale_unadjusted_bands: { P10: 240, P50: 160, P90: 80 },
  scale_adjusted_ops_bands: { P10: 0, P50: 0, P90: 0 },
  scale_unadjusted_ops_bands: { P10: 0, P50: 0, P90: 0 },
  cf_used: 1.25,
  recommended_band: "P50",
});

describe("resultsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("paramsChangedAt 之后 forwardResult 标记 stale", () => {
    const store = useResultsStore();
    store.setForwardResult(sampleForward());
    expect(store.isStale).toBe(false);
    store.markParamsChanged();
    expect(store.isStale).toBe(true);
  });

  it("setForwardResult 清除 stale 标志", () => {
    const store = useResultsStore();
    store.markParamsChanged();
    store.setForwardResult(sampleForward());
    expect(store.isStale).toBe(false);
  });

  it("setReverseResult 写入 reverseResult + 更新 lastComputedAt", () => {
    const store = useResultsStore();
    const r = sampleReverse();
    store.setReverseResult(r);
    expect(store.reverseResult).toEqual(r);
    expect(store.lastComputedAt).toBeGreaterThan(0);
  });

  it("clear() 清空所有结果与时间戳", () => {
    const store = useResultsStore();
    store.setForwardResult(sampleForward());
    store.markParamsChanged();
    store.clear();
    expect(store.forwardResult).toBeNull();
    expect(store.reverseResult).toBeNull();
    expect(store.lastComputedAt).toBe(0);
    expect(store.paramsChangedAt).toBe(0);
  });
});
