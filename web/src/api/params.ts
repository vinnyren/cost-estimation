import { api } from "./client";

export interface EffectiveParams {
  cf: Record<string, number>;
  productivity_dev: Record<string, Record<string, number>>;
  productivity_ops?: Record<string, Record<string, number>>;
  city_rate: Record<string, { dev: number; ops: number; class: string }>;
  factors_dev: Record<string, Record<string, number>>;
  factors_ops: Record<string, Record<string, number>>;
  hours_per_pm: number;
  ops_cost_ratio: { P50: number };
  overrides?: Record<string, unknown>;
}

export const paramsApi = {
  effective: (projectId: number) =>
    api.get<EffectiveParams>(`/api/projects/${projectId}/params/effective`),
  global: () => api.get<EffectiveParams>("/api/params/global"),
  patchGlobal: (body: Partial<EffectiveParams>) =>
    api.patch<EffectiveParams>("/api/params/global", body),
  resetGlobal: () => api.post<EffectiveParams>("/api/params/global/reset"),
  override: (projectId: number, body: Record<string, unknown>) =>
    api.patch<EffectiveParams>(`/api/projects/${projectId}/params/override`, body),
};
