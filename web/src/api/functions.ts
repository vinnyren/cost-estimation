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

export interface FpSnapshotMeta {
  id: number;
  version: number;
  snapshot_at: string | null;
  reason: string | null;
  fp_count: number;
}

export const functionsApi = {
  list: (projectId: string) =>
    api.get<FunctionPoint[]>(`/api/projects/${projectId}/functions`),
  create: (projectId: string, body: Partial<FunctionPoint>) =>
    api.post<FunctionPoint>(`/api/projects/${projectId}/functions`, body),
  patch: (projectId: string, fpId: string, body: Partial<FunctionPoint>) =>
    api.patch<FunctionPoint>(`/api/projects/${projectId}/functions/${fpId}`, body),
  remove: (projectId: string, fpId: string) =>
    api.delete<{ deleted: string }>(`/api/projects/${projectId}/functions/${fpId}`),
  bulk: (projectId: string, items: Partial<FunctionPoint>[]) =>
    api.post<{ written: number }>(`/api/projects/${projectId}/functions/bulk`, { items }),
  snapshots: (projectId: string) =>
    api.get<FpSnapshotMeta[]>(`/api/projects/${projectId}/functions/snapshots`),
  restore: (projectId: string, version: number) =>
    api.post<{ restored_version: number; fp_count: number }>(
      `/api/projects/${projectId}/functions/restore?version=${version}`,
    ),
};
