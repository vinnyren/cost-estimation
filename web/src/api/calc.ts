import { api } from "./client";

export interface ForwardResult {
  scale_adjusted: number;
  effort_pm: { P10: number; P50: number; P90: number };
  cost_yuan: { P10: number; P50: number; P90: number };
  steps?: Array<{ name: string; value: number; note?: string }>;
}

export interface ReverseResult {
  fp_total: { P10: number; P50: number; P90: number };
  recommended_band: "P10" | "P50" | "P90";
}

export const calcApi = {
  forward: (body: { project_id: number }) => api.post<ForwardResult>("/api/calc/forward", body),
  reverse: (body: { project_id: number; target_total: number; other_cost: number }) =>
    api.post<ReverseResult>("/api/calc/reverse", body),
  allocate: (body: { project_id: number; target_us: number; cf: number }) =>
    api.post<{ items: Array<{ id: number; us: number; audit_tag?: string }> }>(
      "/api/calc/allocate",
      body,
    ),
};
