// v2.0 T8 — ParamSnapshot client surface.
//
// Backend (server/app/api/snapshots.py) emits the new {success, data, error}
// envelope, which is incompatible with the legacy unwrap() in client.ts
// (which only recognises {ok, data}). Until the wrapper is unified, we go
// through api.raw (the axios instance) and unwrap the envelope inline. The
// X-Auth-Token interceptor still fires on api.raw, so auth is fine.
import { api, ApiError } from "./client";

export interface ParamSnapshot {
  id: number;
  scope: string;
  label: string | null;
  created_at: string;
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

export const snapshotsApi = {
  async list(scope?: string): Promise<ParamSnapshot[]> {
    const qs = scope ? `?scope=${encodeURIComponent(scope)}` : "";
    const resp = await api.raw.get<NewEnvelope<ParamSnapshot[]>>(
      `/api/params/snapshots${qs}`,
    );
    return unwrapNew<ParamSnapshot[]>(resp.data);
  },

  async create(input: { scope: string; label?: string }): Promise<ParamSnapshot> {
    const resp = await api.raw.post<NewEnvelope<ParamSnapshot>>(
      `/api/params/snapshots`,
      input,
    );
    return unwrapNew<ParamSnapshot>(resp.data);
  },

  async restore(id: number): Promise<unknown> {
    const resp = await api.raw.post<NewEnvelope<unknown>>(
      `/api/params/snapshots/${id}/restore`,
    );
    return unwrapNew<unknown>(resp.data);
  },

  async remove(id: number): Promise<void> {
    // DELETE returns 204 No Content — no envelope to unwrap.
    await api.raw.delete(`/api/params/snapshots/${id}`);
  },
};
