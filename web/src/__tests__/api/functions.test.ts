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

import { functionsApi } from "@/api/functions";
import { api } from "@/api/client";

describe("functionsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("list 调 GET /api/projects/:id/functions", async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    const result = await functionsApi.list("p-11");
    expect(api.get).toHaveBeenCalledWith("/api/projects/p-11/functions");
    expect(result).toEqual([]);
  });

  it("patch 调 PATCH /api/projects/:pid/functions/:fpid", async () => {
    const body = { ufp: 7 };
    (api.patch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ id: "f-5", ...body });
    const result = await functionsApi.patch("p-11", "f-5", body);
    expect(api.patch).toHaveBeenCalledWith("/api/projects/p-11/functions/f-5", body);
    expect(result).toMatchObject({ id: "f-5", ufp: 7 });
  });

  it("bulk 调 POST /api/projects/:id/functions/bulk 并包装 items", async () => {
    const items = [{ ufp: 1 }, { ufp: 2 }];
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ written: 2 });
    const result = await functionsApi.bulk("p-11", items);
    expect(api.post).toHaveBeenCalledWith("/api/projects/p-11/functions/bulk", { items });
    expect(result).toEqual({ written: 2 });
  });

  it("restore 调 POST /api/projects/:id/functions/restore?version=N", async () => {
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
    await functionsApi.restore("p-11", 3);
    expect(api.post).toHaveBeenCalledWith("/api/projects/p-11/functions/restore?version=3");
  });

  it("acceptDrafts 调 POST /api/projects/:id/functions/accept-drafts", async () => {
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      accepted: 3,
    });
    const result = await functionsApi.acceptDrafts("p-1");
    expect(api.post).toHaveBeenCalledWith(
      "/api/projects/p-1/functions/accept-drafts",
    );
    expect(result).toEqual({ accepted: 3 });
  });
});
