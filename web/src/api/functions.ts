import { api } from "./client";

export type FpCategory = "EI" | "EO" | "EQ" | "ILF" | "EIF";
export type FpComplexity = "low" | "average" | "high";
export type FpReuseLevel = "low" | "high";
export type FpModifyType = "new" | "modify" | "delete";
export type FpSource =
  | "manual"
  | "imported"
  | "ai_extracted"
  | "claude_draft"
  | "allocator";

export interface FunctionPoint {
  id: string;
  project_id: string;
  subsystem?: string;
  l1_module?: string;
  l2_module?: string;
  description?: string;
  name?: string;
  category: FpCategory;
  complexity: FpComplexity;
  ufp: number;
  reuse_level?: FpReuseLevel;
  modify_type?: FpModifyType;
  us: number;
  source?: FpSource;
  locked?: boolean;
  notes?: string;
  ord?: number;
  version: number;
}

export const functionsApi = {
  list: (projectId: string) =>
    api.get<FunctionPoint[]>(`/api/projects/${projectId}/functions`),
  patch: (projectId: string, fpId: string, body: Partial<FunctionPoint>) =>
    api.patch<FunctionPoint>(`/api/projects/${projectId}/functions/${fpId}`, body),
  bulk: (projectId: string, items: Partial<FunctionPoint>[]) =>
    api.post<{ written: number }>(`/api/projects/${projectId}/functions/bulk`, { items }),
  restore: (projectId: string, version: number) =>
    api.post<void>(`/api/projects/${projectId}/functions/restore?version=${version}`),
};
