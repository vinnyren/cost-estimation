import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useResultsStore } from "@/stores/results";

describe("resultsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("paramsChangedAt 之后 forwardResult 标记 stale", () => {
    const store = useResultsStore();
    store.setForwardResult({
      scale_adjusted: 332.75,
      effort_pm: { P10: 50, P50: 80, P90: 110 },
      cost_yuan: { P10: 300000, P50: 489180, P90: 700000 },
    });
    expect(store.isStale).toBe(false);
    store.markParamsChanged();
    expect(store.isStale).toBe(true);
  });

  it("setForwardResult 清除 stale 标志", () => {
    const store = useResultsStore();
    store.markParamsChanged();
    store.setForwardResult({
      scale_adjusted: 100,
      effort_pm: { P10: 1, P50: 2, P90: 3 },
      cost_yuan: { P10: 1, P50: 2, P90: 3 },
    });
    expect(store.isStale).toBe(false);
  });
});
