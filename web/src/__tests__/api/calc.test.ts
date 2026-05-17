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

import { calcApi } from "@/api/calc";
import { api } from "@/api/client";

describe("calcApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("forward 调 POST /api/calc/forward 并透传 body", async () => {
    const body = { project_id: "p-1" };
    const reply = {
      scale_us: 80,
      scale_adjusted: 100,
      cf_used: 1.25,
      effort_dev_hours: { P10: 800, P50: 1600, P90: 2400 },
      effort_ops_hours: { P10: 0, P50: 0, P90: 0 },
      cost_dev_yuan: { P10: 10, P50: 20, P90: 30 },
      cost_ops_yuan: { P10: 0, P50: 0, P90: 0 },
      cost_other_yuan: 0,
      cost_total_yuan: { P10: 10, P50: 20, P90: 30 },
    };
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(reply);
    const result = await calcApi.forward(body);
    expect(api.post).toHaveBeenCalledWith("/api/calc/forward", body);
    expect(result).toEqual(reply);
  });

  it("reverse 调 POST /api/calc/reverse 并透传 body", async () => {
    const body = { project_id: "p-1", target_total: 1_000_000, other_cost: 50_000 };
    const reply = {
      budget_for_dev: 950_000,
      budget_for_ops: 0,
      scale_adjusted_bands: { P10: 300, P50: 200, P90: 100 },
      scale_unadjusted_bands: { P10: 240, P50: 160, P90: 80 },
      cf_used: 1.25,
      recommended_band: "P50" as const,
    };
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(reply);
    const result = await calcApi.reverse(body);
    expect(api.post).toHaveBeenCalledWith("/api/calc/reverse", body);
    expect(result).toEqual(reply);
  });

  it("allocate 调 POST /api/calc/allocate 并透传 body", async () => {
    const body = {
      project_id: "p-1",
      target_us: 200,
      cf: 1.0,
      drafts: [{ name: "A", weight: 1 }],
    };
    const reply = [
      { name: "A", us: 200, locked: false, audit_tag: "budget_derived" },
    ];
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(reply);
    const result = await calcApi.allocate(body);
    expect(api.post).toHaveBeenCalledWith("/api/calc/allocate", body);
    expect(result).toEqual(reply);
  });
});
