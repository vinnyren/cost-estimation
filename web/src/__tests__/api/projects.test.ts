import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    raw: {
      get: vi.fn(),
      post: vi.fn(),
      delete: vi.fn(),
    },
  },
  ApiError: class ApiError extends Error {},
}));

import { projectsApi } from "@/api/projects";
import { api } from "@/api/client";

describe("projectsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("list 通过 query 调 GET /api/projects 并返回 data 数组（新 envelope）", async () => {
    // T20: list() now delegates to query() which speaks the new {success,data,meta}
    // envelope through api.raw.get, not the legacy api.get + unwrap path.
    (api.raw.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        success: true,
        data: [{ id: "p-1", name: "p1" }],
        meta: { total: 1, page: 1, size: 50 },
      },
    });
    const result = await projectsApi.list();
    expect(api.raw.get).toHaveBeenCalledWith("/api/projects");
    expect(result).toEqual([{ id: "p-1", name: "p1" }]);
  });

  it("get 调 GET /api/projects/:id", async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ id: "p-7" });
    const result = await projectsApi.get("p-7");
    expect(api.get).toHaveBeenCalledWith("/api/projects/p-7");
    expect(result).toEqual({ id: "p-7" });
  });

  it("create 调 POST /api/projects 并透传 body", async () => {
    const body = { name: "n1", mode: "forward" as const };
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ id: "p-1", ...body });
    const result = await projectsApi.create(body);
    expect(api.post).toHaveBeenCalledWith("/api/projects", body);
    expect(result).toMatchObject({ id: "p-1" });
  });

  it("patch 调 PATCH /api/projects/:id 并透传 body", async () => {
    const body = { name: "n2" };
    (api.patch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ id: "p-3", ...body });
    const result = await projectsApi.patch("p-3", body);
    expect(api.patch).toHaveBeenCalledWith("/api/projects/p-3", body);
    expect(result).toMatchObject({ id: "p-3", name: "n2" });
  });

  it("remove 调 DELETE /api/projects/:id", async () => {
    (api.delete as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
    await projectsApi.remove("p-9");
    expect(api.delete).toHaveBeenCalledWith("/api/projects/p-9");
  });
});
