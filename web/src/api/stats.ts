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
    const qs = month ? `?month=${encodeURIComponent(month)}` : "";
    return api.get<ProjectStats>(`/api/projects/stats${qs}`);
  },
};
