import { describe, it, expect, beforeEach } from "vitest";
import { createMemoryHistory } from "vue-router";
import { extractTokenFromUrl, createRouterFor } from "@/router";

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

  it("路由表包含 5 屏", () => {
    const router = createRouterFor(createMemoryHistory());
    const names = router.getRoutes().map((r) => r.name);
    expect(names).toEqual(
      expect.arrayContaining([
        "project-list",
        "project-wizard",
        "fp-editor",
        "param-manager",
        "result-view",
      ]),
    );
  });
});
