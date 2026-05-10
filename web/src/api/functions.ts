import { api } from "./client";

export type FpCategory = "EI" | "EO" | "EQ" | "ILF" | "EIF";
export type FpSource =
  | "manual"
  | "imported"
  | "ai_extracted"
  | "claude_draft"
  | "allocator";

export interface FunctionPoint {
  id: number;
  project_id: number;
  subsystem: string;
  module_l1: string;
  module_l2?: string;
  description: string;
  category: FpCategory;
  ufp: number;
  reuse_ratio: number;
  modify_ratio: number;
  us: number;
  source: FpSource;
  audit_tag?: string;
  version: number;
}

export const functionsApi = {
  list: (projectId: number) =>
    api.get<{ items: FunctionPoint[] }>(`/api/projects/${projectId}/functions`),
  patch: (projectId: number, fpId: number, body: Partial<FunctionPoint>) =>
    api.patch<FunctionPoint>(`/api/projects/${projectId}/functions/${fpId}`, body),
  bulk: (projectId: number, items: Partial<FunctionPoint>[]) =>
    api.post<{ items: FunctionPoint[] }>(`/api/projects/${projectId}/functions/bulk`, { items }),
  restore: (projectId: number, version: number) =>
    api.post<void>(`/api/projects/${projectId}/functions/restore?version=${version}`),
};
