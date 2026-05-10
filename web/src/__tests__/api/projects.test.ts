import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  ApiError: class ApiError extends Error {},
}));

import { projectsApi } from "@/api/projects";
import { api } from "@/api/client";

describe("projectsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("list 调 GET /api/projects", async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ items: [] });
    const result = await projectsApi.list();
    expect(api.get).toHaveBeenCalledWith("/api/projects");
    expect(result).toEqual({ items: [] });
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
