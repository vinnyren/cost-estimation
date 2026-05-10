import { api } from "./client";

export type ProjectMode = "forward" | "reverse";
export type ProjectType = "dev_only" | "ops_only" | "dev_and_ops";
export type ProjectPhase =
  | "budget"
  | "bidding"
  | "planning"
  | "change"
  | "settled";

export interface Project {
  id: string;
  name: string;
  project_type: ProjectType;
  mode: ProjectMode;
  city: string;
  industry: string;
  phase: ProjectPhase;
  basis_data_ver: string;
  client?: string;
  evaluator?: string;
  target_cost?: number;
  other_cost?: number;
  include_ops?: boolean;
  alpha_dev?: number;
  fp_method?: "nesma_estimated" | "ifpug" | "quick";
  total_fp?: number;
  total_cost?: number;
  created_at: string;
  updated_at: string;
}

export const projectsApi = {
  list: () => api.get<Project[]>("/api/projects"),
  get: (id: string) => api.get<Project>(`/api/projects/${id}`),
  create: (body: Partial<Project>) => api.post<Project>("/api/projects", body),
  patch: (id: string, body: Partial<Project>) =>
    api.patch<Project>(`/api/projects/${id}`, body),
  remove: (id: string) => api.delete<void>(`/api/projects/${id}`),
};
