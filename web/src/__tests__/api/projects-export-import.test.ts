import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  api: {
    raw: { post: vi.fn() },
  },
  ApiError: class ApiError extends Error {},
}));

import { projectsApi } from "@/api/projects";
import { api } from "@/api/client";

describe("projectsApi 导出/导入 (v2.7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("exportProjects 调 POST /api/projects/export 并返回 bundle", async () => {
    const bundle = { version: "2.7", exported_at: "x", projects: [] };
    (api.raw.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { success: true, data: bundle, error: null },
    });
    const result = await projectsApi.exportProjects(["p-1", "p-2"]);
    expect(api.raw.post).toHaveBeenCalledWith("/api/projects/export", {
      ids: ["p-1", "p-2"],
    });
    expect(result).toEqual(bundle);
  });

  it("importProjects 调 POST /api/projects/import 并返回结果", async () => {
    const bundle = { version: "2.7", exported_at: "x", projects: [] };
    (api.raw.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        success: true,
        data: { imported: 2, project_ids: ["n-1", "n-2"] },
        error: null,
      },
    });
    const result = await projectsApi.importProjects(bundle);
    expect(api.raw.post).toHaveBeenCalledWith("/api/projects/import", bundle);
    expect(result).toEqual({ imported: 2, project_ids: ["n-1", "n-2"] });
  });

  it("importProjects 在 success=false 时抛 ApiError", async () => {
    (api.raw.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        success: false,
        data: null,
        error: { code: "INVALID_BUNDLE", message: "格式非法" },
      },
    });
    await expect(
      projectsApi.importProjects({ version: "2.7", exported_at: "x", projects: [] }),
    ).rejects.toThrow();
  });
});
