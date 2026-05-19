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

import { paramsApi } from "@/api/params";
import { api } from "@/api/client";

describe("paramsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("effective 调 GET /api/projects/:id/params/effective", async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ cf: {} });
    const result = await paramsApi.effective("p-42");
    expect(api.get).toHaveBeenCalledWith("/api/projects/p-42/params/effective");
    expect(result).toEqual({ cf: {} });
  });

  it("global 调 GET /api/params/global", async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ cf: { x: 1 } });
    const result = await paramsApi.global();
    expect(api.get).toHaveBeenCalledWith("/api/params/global");
    expect(result).toEqual({ cf: { x: 1 } });
  });

  it("patchGlobal 调 PATCH /api/params/global 发送 {key, value}", async () => {
    (api.patch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ updated: "hours_per_pm" });
    const result = await paramsApi.patchGlobal("hours_per_pm", 160);
    expect(api.patch).toHaveBeenCalledWith("/api/params/global", { key: "hours_per_pm", value: 160 });
    expect(result).toMatchObject({ updated: "hours_per_pm" });
  });

  it("resetGlobal 调 POST /api/params/global/reset", async () => {
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ cf: {} });
    const result = await paramsApi.resetGlobal();
    expect(api.post).toHaveBeenCalledWith("/api/params/global/reset");
    expect(result).toEqual({ cf: {} });
  });

  it("override 调 PATCH /api/projects/:id/params/override 并透传 body", async () => {
    const body = { "cf.scale": 1.2 };
    (api.patch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ overrides: body });
    const result = await paramsApi.override("p-7", body);
    expect(api.patch).toHaveBeenCalledWith("/api/projects/p-7/params/override", body);
    expect(result).toMatchObject({ overrides: body });
  });
});

describe("paramsApi.patchGlobal — 逐 leaf key", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it("patchGlobal 发送 {key, value} 到 /api/params/global", async () => {
    (api.patch as ReturnType<typeof vi.fn>).mockResolvedValue({ updated: "x" });
    await paramsApi.patchGlobal("scale_change.modify", 0.85);
    expect(api.patch).toHaveBeenCalledWith("/api/params/global", {
      key: "scale_change.modify",
      value: 0.85,
    });
  });

  it("resetGlobal POST /api/params/global/reset", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({});
    await paramsApi.resetGlobal();
    expect(api.post).toHaveBeenCalledWith("/api/params/global/reset");
  });
});
