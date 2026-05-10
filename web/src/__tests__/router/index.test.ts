import { describe, it, expect, beforeEach, vi } from "vitest";
import { createMemoryHistory } from "vue-router";
import { extractTokenFromUrl, createRouterFor, setDirtyChecker } from "@/router";

describe("router", () => {
  beforeEach(() => sessionStorage.clear());

  it("从 URL 提取 ?t= 参数并写入 sessionStorage", () => {
    extractTokenFromUrl("http://127.0.0.1:5173/?t=abc-123");
    expect(sessionStorage.getItem("auth_token")).toBe("abc-123");
  });

  it("URL 无 token 时不覆盖已存在的 sessionStorage 值", () => {
    sessionStorage.setItem("auth_token", "existing");
    extractTokenFromUrl("http://127.0.0.1:5173/");
    expect(sessionStorage.getItem("auth_token")).toBe("existing");
  });

  it("路由表包含 5 屏 + 每条 props 函数能从 route 提取 projectId", () => {
    const router = createRouterFor(createMemoryHistory());
    const records = router.getRoutes();
    const names = records.map((r) => r.name);
    expect(names).toEqual(
      expect.arrayContaining([
        "project-list",
        "project-wizard",
        "fp-editor",
        "param-manager",
        "result-view",
      ]),
    );
    // 显式调用 props 函数（带 id 的 3 个屏），确保函数执行
    const idRoutes = records.filter((r) =>
      ["fp-editor", "param-manager", "result-view"].includes(String(r.name)),
    );
    for (const r of idRoutes) {
      const propsFn = r.props.default as unknown as (route: {
        params: { id: string };
      }) => { projectId: number };
      expect(typeof propsFn).toBe("function");
      const out = propsFn({ params: { id: "42" } });
      expect(out.projectId).toBe(42);
    }
  });

  it("setDirtyChecker 注入 → beforeEach 阻断导航", async () => {
    const router = createRouterFor(createMemoryHistory());
    await router.push("/");
    await router.isReady();
    setDirtyChecker(router, () => true);
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const before = router.currentRoute.value.fullPath;
    await router.push("/projects/new").catch(() => {});
    expect(confirmSpy).toHaveBeenCalled();
    expect(router.currentRoute.value.fullPath).toBe(before);
    confirmSpy.mockRestore();
  });

  it("setDirtyChecker(false) → beforeEach 不阻拦", async () => {
    const router = createRouterFor(createMemoryHistory());
    await router.push("/");
    await router.isReady();
    setDirtyChecker(router, () => false);
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    await router.push("/projects/new").catch(() => {});
    expect(confirmSpy).not.toHaveBeenCalled();
  });
});
