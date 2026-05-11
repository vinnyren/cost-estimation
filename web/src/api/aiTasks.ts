import { api } from "./client";

export type AiTaskKind = "extract" | "allocate";
export type AiTaskStatus = "queued" | "running" | "done" | "failed";

export interface AiTask {
  id: string;
  project_id: string;
  kind: AiTaskKind;
  status: AiTaskStatus;
  progress_pct: number;
  stage_log: string;
  output_json: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

// Endpoints return raw Pydantic JSON (no {ok, data} envelope) — use api.raw to skip unwrap.
export const aiTasksApi = {
  async list(projectId: string): Promise<AiTask[]> {
    const r = await api.raw.get<AiTask[]>(
      `/api/ai-tasks?project_id=${encodeURIComponent(projectId)}`,
    );
    return r.data;
  },
  async get(id: string): Promise<AiTask> {
    const r = await api.raw.get<AiTask>(`/api/ai-tasks/${encodeURIComponent(id)}`);
    return r.data;
  },
};
