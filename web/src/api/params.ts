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
  /**
   * 规模变更因子 — CSBMK®-202510 暂未提供，但 v2 后续可能通过 override 注入。
   * 形态：scalar map（add / remove / modify / convert / threshold → number），
   * 或嵌套 map（细分变更类型）。两种都按 leaf 渲染。
   */
  scale_change?: Record<string, number | Record<string, number>>;
  overrides?: Record<string, unknown>;
}

export const paramsApi = {
  effective: (projectId: string) =>
    api.get<EffectiveParams>(`/api/projects/${projectId}/params/effective`),
  global: () => api.get<EffectiveParams>("/api/params/global"),
  patchGlobal: (key: string, value: unknown) =>
    api.patch<{ updated: string }>("/api/params/global", { key, value }),
  resetGlobal: () => api.post<EffectiveParams>("/api/params/global/reset"),
  override: (projectId: string, body: Record<string, unknown>) =>
    api.patch<EffectiveParams>(`/api/projects/${projectId}/params/override`, body),
};
