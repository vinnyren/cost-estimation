import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  api: {
    raw: { get: vi.fn() },
  },
}));

import { statsApi } from "@/api/stats";
import { api } from "@/api/client";

describe("statsApi.getProjectStats", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.raw.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        counts: { total: 0, draft: 0, in_progress: 0, archived: 0, delivered: 0 },
        monthly_count: 0,
        monthly_p50_sum: 0,
        monthly_growth_pct: 0,
      },
    });
  });

  it("calls /api/projects/stats without query when no month", async () => {
    await statsApi.getProjectStats();
    expect(api.raw.get).toHaveBeenCalledWith("/api/projects/stats");
  });

  it("calls with encoded month query", async () => {
    await statsApi.getProjectStats("2026-04");
    expect(api.raw.get).toHaveBeenCalledWith("/api/projects/stats?month=2026-04");
  });
});
