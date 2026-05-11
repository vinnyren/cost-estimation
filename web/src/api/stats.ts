import { api } from "./client";

export interface ProjectStatsCounts {
  total: number;
  draft: number;
  in_progress: number;
  archived: number;
  delivered: number;
}

export interface ProjectStats {
  counts: ProjectStatsCounts;
  monthly_count: number;
  monthly_p50_sum: number;
  monthly_growth_pct: number;
}

export const statsApi = {
  async getProjectStats(month?: string): Promise<ProjectStats> {
    // The stats endpoint returns raw ProjectStats (not the ok/data envelope),
    // so use api.raw to bypass the unwrap wrapper.
    const qs = month ? `?month=${encodeURIComponent(month)}` : "";
    const resp = await api.raw.get<ProjectStats>(`/api/projects/stats${qs}`);
    return resp.data;
  },
};
