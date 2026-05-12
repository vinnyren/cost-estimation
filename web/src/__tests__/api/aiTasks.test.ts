import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    raw: {
      get: vi.fn(),
      post: vi.fn(),
    },
  },
  ApiError: class ApiError extends Error {},
}));

import { aiTasksApi } from "@/api/aiTasks";
import { api } from "@/api/client";

describe("aiTasksApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.raw.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: [] });
  });

  it("list calls /api/ai-tasks?project_id=X", async () => {
    await aiTasksApi.list("p-001");
    expect(api.raw.get).toHaveBeenCalledWith("/api/ai-tasks?project_id=p-001");
  });

  it("get calls /api/ai-tasks/<id>", async () => {
    (api.raw.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { id: "t-1" } });
    await aiTasksApi.get("t-1");
    expect(api.raw.get).toHaveBeenCalledWith("/api/ai-tasks/t-1");
  });

  it("create POSTs to /api/ai-tasks with project_id+kind", async () => {
    (api.raw.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { id: "t-new", status: "queued" } });
    const r = await aiTasksApi.create("p-1", "extract");
    expect(api.raw.post).toHaveBeenCalledWith("/api/ai-tasks", { project_id: "p-1", kind: "extract" });
    expect(r.id).toBe("t-new");
  });

  it("start POSTs to /api/ai-tasks/<id>/start and returns pid", async () => {
    (api.raw.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { pid: 9999 } });
    const r = await aiTasksApi.start("t-1");
    expect(api.raw.post).toHaveBeenCalledWith("/api/ai-tasks/t-1/start");
    expect(r.pid).toBe(9999);
  });

  it("stop POSTs to /api/ai-tasks/<id>/stop and returns stopped flag", async () => {
    (api.raw.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { stopped: true } });
    const r = await aiTasksApi.stop("t-1");
    expect(api.raw.post).toHaveBeenCalledWith("/api/ai-tasks/t-1/stop");
    expect(r.stopped).toBe(true);
  });
});
