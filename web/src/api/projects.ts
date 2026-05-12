import { api, ApiError } from "./client";

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

// v2.0 T8 — query/copy go through the new {success,data,meta} envelope.
// v2.0 T20 — list() now delegates to query() so both speak the new envelope.
// Callers that only care about the array (e.g. store.fetchAll) keep their
// existing Promise<Project[]> contract; callers that need meta/filter/sort
// (e.g. ProjectList toolbar) call query() directly.
export interface ProjectQuery {
  q?: string;
  city?: string;
  industry?: string;
  phase?: ProjectPhase;
  mode?: ProjectMode;
  sort?: "created_at" | "updated_at" | "name" | "target_cost";
  order?: "asc" | "desc";
  page?: number;
  size?: number;
}

export interface ProjectQueryResult {
  data: Project[];
  meta: { total: number; page: number; size: number };
}

interface NewEnvelope<T> {
  success: boolean;
  data: T;
  error: { code: string; message?: string; details?: Record<string, unknown> } | null;
  meta?: { total: number; page: number; size: number };
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

function buildQueryString(opts: ProjectQuery): string {
  const params = new URLSearchParams();
  // Filter out undefined, null, and empty-string values — the backend treats
  // missing params as "no filter" and we don't want empty filters polluting
  // the URL.
  (Object.keys(opts) as Array<keyof ProjectQuery>).forEach((key) => {
    const value = opts[key];
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });
  return params.toString();
}

export const projectsApi = {
  // list() returns just the array for backwards compatibility with the
  // projects store; full meta/filter/sort go through query().
  async list(): Promise<Project[]> {
    const { data } = await projectsApi.query();
    return data;
  },
  get: (id: string) => api.get<Project>(`/api/projects/${id}`),
  create: (body: Partial<Project>) => api.post<Project>("/api/projects", body),
  update: (id: string, body: Partial<Project>) =>
    api.patch<Project>(`/api/projects/${id}`, body),
  patch: (id: string, body: Partial<Project>) =>
    api.patch<Project>(`/api/projects/${id}`, body),
  remove: (id: string) => api.delete<void>(`/api/projects/${id}`),

  async query(opts: ProjectQuery = {}): Promise<ProjectQueryResult> {
    const qs = buildQueryString(opts);
    const url = `/api/projects${qs ? "?" + qs : ""}`;
    const resp = await api.raw.get<NewEnvelope<Project[]>>(url);
    const data = unwrapNew<Project[]>(resp.data);
    const meta = (resp.data as NewEnvelope<Project[]>).meta ?? {
      total: data.length,
      page: 1,
      size: data.length,
    };
    return { data, meta };
  },

  async copy(srcId: string, name: string): Promise<Project> {
    const resp = await api.raw.post<NewEnvelope<Project>>(
      `/api/projects/${srcId}/copy`,
      { name },
    );
    return unwrapNew<Project>(resp.data);
  },
};
