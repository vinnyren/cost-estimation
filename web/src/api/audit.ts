// v2.0 T8 — Project audit-log client surface.
//
// Backend (server/app/api/audit.py) emits the new {success, data, error}
// envelope, so we go through api.raw and unwrap inline (same pattern as
// snapshots.ts — see that file for the rationale).
import { api, ApiError } from "./client";

export interface AuditEntry {
  id: number;
  project_id: string;
  ts: string;
  actor: string | null;
  action: string;
  target: string | null;
  diff_json: string | null;
}

export interface AuditListOptions {
  limit?: number;
  beforeId?: number;
}

interface NewEnvelope<T> {
  success: boolean;
  data: T;
  error: { code: string; message?: string; details?: Record<string, unknown> } | null;
}

function unwrapNew<T>(payload: unknown): T {
  if (!payload || typeof payload !== "object") {
    throw new ApiError("INVALID_RESPONSE", "Server returned malformed envelope");
  }
  const env = payload as NewEnvelope<T>;
  if (env.success) return env.data;
  const e = env.error ?? { code: "UNKNOWN", message: "" };
  throw new ApiError(e.code, e.message ?? "", e.details);
}

export const auditApi = {
  async list(projectId: string, opts: AuditListOptions = {}): Promise<AuditEntry[]> {
    const params = new URLSearchParams();
    if (opts.limit !== undefined) params.set("limit", String(opts.limit));
    if (opts.beforeId !== undefined) params.set("before_id", String(opts.beforeId));
    const qs = params.toString();
    const url = `/api/projects/${projectId}/audit${qs ? "?" + qs : ""}`;
    const resp = await api.raw.get<NewEnvelope<AuditEntry[]>>(url);
    return unwrapNew<AuditEntry[]>(resp.data);
  },
};
