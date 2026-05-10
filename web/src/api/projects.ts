import { api } from "./client";

export type ProjectMode = "forward" | "reverse";

export interface Project {
  id: number;
  name: string;
  mode: ProjectMode;
  city: string;
  industry: string;
  stage: string;
  total_fp?: number;
  total_cost?: number;
  created_at: string;
  updated_at: string;
}

export const projectsApi = {
  list: () => api.get<{ items: Project[] }>("/api/projects"),
  get: (id: number) => api.get<Project>(`/api/projects/${id}`),
  create: (body: Partial<Project>) => api.post<Project>("/api/projects", body),
  patch: (id: number, body: Partial<Project>) => api.patch<Project>(`/api/projects/${id}`, body),
  remove: (id: number) => api.delete<void>(`/api/projects/${id}`),
};
