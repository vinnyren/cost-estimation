import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  api: {
    raw: { get: vi.fn() },
  },
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
});
