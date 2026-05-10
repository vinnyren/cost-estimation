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
    const body = { project_id: 1 };
    const reply = {
      scale_adjusted: 100,
      effort_pm: { P10: 1, P50: 2, P90: 3 },
      cost_yuan: { P10: 10, P50: 20, P90: 30 },
    };
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(reply);
    const result = await calcApi.forward(body);
    expect(api.post).toHaveBeenCalledWith("/api/calc/forward", body);
    expect(result).toEqual(reply);
  });

  it("reverse 调 POST /api/calc/reverse 并透传 body", async () => {
    const body = { project_id: 1, target_total: 1_000_000, other_cost: 50_000 };
    const reply = {
      fp_total: { P10: 100, P50: 200, P90: 300 },
      recommended_band: "P50" as const,
    };
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(reply);
    const result = await calcApi.reverse(body);
    expect(api.post).toHaveBeenCalledWith("/api/calc/reverse", body);
    expect(result).toEqual(reply);
  });

  it("allocate 调 POST /api/calc/allocate 并透传 body", async () => {
    const body = { project_id: 1, target_us: 200, cf: 1.0 };
    const reply = { items: [{ id: 1, us: 50 }] };
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(reply);
    const result = await calcApi.allocate(body);
    expect(api.post).toHaveBeenCalledWith("/api/calc/allocate", body);
    expect(result).toEqual(reply);
  });
});
