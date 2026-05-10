import { describe, it, expect, vi } from "vitest";
import { nextTick } from "vue";
import { useApi } from "@/composables/useApi";
import { ApiError } from "@/api/client";

describe("useApi", () => {
  it("初始 state=idle", () => {
    const { state } = useApi(() => Promise.resolve("ok"));
    expect(state.value).toBe("idle");
  });

  it("调用过程中 state=loading", async () => {
    let resolve: (v: string) => void = () => {};
    const fn = (): Promise<string> => new Promise<string>((r) => (resolve = r));
    const { state, run } = useApi(fn);
    const p = run();
    await nextTick();
    expect(state.value).toBe("loading");
    resolve("ok");
    await p;
    expect(state.value).toBe("success");
  });

  it("成功后 data 可读、error=null", async () => {
    const { state, data, error, run } = useApi(() => Promise.resolve(42));
    await run();
    expect(state.value).toBe("success");
    expect(data.value).toBe(42);
    expect(error.value).toBeNull();
  });

  it("失败后 state=error，error 暴露 ApiError", async () => {
    const fn = vi.fn().mockRejectedValue(new ApiError("INVALID_PARAM", "x"));
    const { state, error, run } = useApi(fn);
    await expect(run()).rejects.toThrow();
    expect(state.value).toBe("error");
    expect(error.value).toMatchObject({ code: "INVALID_PARAM", message: "x" });
  });

  it("reset 回到 idle", async () => {
    const { state, data, run, reset } = useApi(() => Promise.resolve(1));
    await run();
    reset();
    expect(state.value).toBe("idle");
    expect(data.value).toBeNull();
  });
});
