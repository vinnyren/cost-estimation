import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";

vi.mock("@/api/params", () => ({
  paramsApi: {
    effective: vi.fn(),
    override: vi.fn(),
  },
}));

import { useParamsStore } from "@/stores/params";
import { paramsApi } from "@/api/params";

describe("paramsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("loadFor 写入 effective/overrides/loadedFor", async () => {
    (paramsApi.effective as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      cf: { x: 1 },
      overrides: { "cf.x": 2 },
    });
    const store = useParamsStore();
    await store.loadFor("p-7");
    expect(store.effective).toEqual({ cf: { x: 1 }, overrides: { "cf.x": 2 } });
    expect(store.overrides).toEqual({ "cf.x": 2 });
    expect(store.loadedFor).toBe("p-7");
  });

  it("loadFor 处理无 overrides 字段", async () => {
    (paramsApi.effective as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      cf: { x: 1 },
    });
    const store = useParamsStore();
    await store.loadFor("p-7");
    expect(store.overrides).toEqual({});
  });

  it("applyOverride 调 API 并写回 effective/overrides", async () => {
    (paramsApi.override as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      cf: { x: 5 },
      overrides: { "cf.x": 5 },
    });
    const store = useParamsStore();
    await store.applyOverride("p-3", { "cf.x": 5 });
    expect(paramsApi.override).toHaveBeenCalledWith("p-3", { "cf.x": 5 });
    expect(store.overrides).toEqual({ "cf.x": 5 });
  });

  it("isOverridden 命中直接 key", async () => {
    (paramsApi.effective as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      overrides: { "cf.scale": 1.2 },
    });
    const store = useParamsStore();
    await store.loadFor("p-1");
    expect(store.isOverridden("cf.scale")).toBe(true);
    expect(store.isOverridden("cf.unknown")).toBe(false);
  });

  it("isOverridden 命中嵌套 path（如 city_rate.北京.dev）", async () => {
    (paramsApi.effective as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      overrides: { city_rate: { 北京: { dev: 200 } } },
    });
    const store = useParamsStore();
    await store.loadFor("p-1");
    expect(store.isOverridden("city_rate.北京.dev")).toBe(true);
    expect(store.isOverridden("city_rate.上海.dev")).toBe(false);
  });
});
