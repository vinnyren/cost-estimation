import axios, { type AxiosInstance, type AxiosResponse } from "axios";
import type { ApiEnvelope } from "./types";

export const AUTH_TOKEN_KEY = "auth_token";

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * 从一个错误响应体里提取 ApiError。后端有两种错误形态：
 *  1) 业务信封 `{ok:false, error:{code,message,details}}`（2xx，由 unwrap 处理）
 *  2) FastAPI HTTPException → `{detail:{error:{code,problem,fix,...}}}` 或
 *     `{detail:"字符串"}`（非 2xx）。早期版本只看 `data.error`，导致 HTTPException
 *     的 code/problem/fix 全丢失，前端只能显示「Request failed with status code 400」。
 */
interface RawErrorEnvelope {
  code?: string;
  message?: string;
  problem?: string;
  fix?: string;
  details?: Record<string, unknown>;
}

function apiErrorFromResponseData(data: unknown): ApiError | null {
  if (!data || typeof data !== "object") return null;
  const d = data as {
    error?: RawErrorEnvelope;
    detail?: string | { error?: RawErrorEnvelope };
  };
  const env =
    d.error ?? (typeof d.detail === "object" ? d.detail?.error : undefined);
  if (env?.code) {
    // fix 是面向用户的可行动建议，优先展示；problem 次之，最后兜底 code。
    const message = env.message || env.fix || env.problem || env.code;
    return new ApiError(env.code, message, env.details);
  }
  if (typeof d.detail === "string" && d.detail) {
    return new ApiError("REQUEST_FAILED", d.detail);
  }
  return null;
}

function unwrap<T>(resp: AxiosResponse<ApiEnvelope<T>>): T {
  if (!resp.data || typeof resp.data !== "object") {
    throw new ApiError("INVALID_RESPONSE", "Server returned malformed envelope");
  }
  if (resp.data.ok) {
    return resp.data.data;
  }
  throw new ApiError(resp.data.error.code, resp.data.error.message, resp.data.error.details);
}

function getToken(): string {
  return sessionStorage.getItem(AUTH_TOKEN_KEY) ?? "";
}

export interface Client {
  get<T>(url: string, params?: Record<string, unknown>): Promise<T>;
  post<T>(url: string, body?: unknown, config?: { headers?: Record<string, string> }): Promise<T>;
  patch<T>(url: string, body?: unknown): Promise<T>;
  delete<T>(url: string): Promise<T>;
  raw: AxiosInstance;
}

export function createClient(): Client {
  // Note: we intentionally do NOT set a default Content-Type on axios.create.
  // axios will infer "application/json" for plain objects and generate the
  // correct multipart/form-data boundary for FormData bodies. Locking the
  // header to JSON would corrupt multipart uploads (no boundary).
  const instance = axios.create({
    baseURL: "",
    timeout: 30_000,
    headers: { "X-Requested-With": "XMLHttpRequest" },
  });

  // Single token-injection point. Method-level callers (get/post/patch/delete)
  // and direct `api.raw.*` callers (e.g. reports.download with responseType
  // blob) all flow through here. Use immutable spread — the global coding
  // style forbids mutating shared objects in-place.
  instance.interceptors.request.use((config) => {
    const token = getToken();
    if (!token) return config;
    const merged = {
      ...config,
      headers: { ...(config.headers ?? {}), "X-Auth-Token": token },
    };
    return merged as unknown as typeof config;
  });

  instance.interceptors.response.use(
    (resp) => resp,
    (err: unknown) => {
      const e = err as { response?: { data?: unknown }; message?: string };
      const apiErr = apiErrorFromResponseData(e.response?.data);
      if (apiErr) return Promise.reject(apiErr);
      return Promise.reject(new ApiError("NETWORK_ERROR", e.message ?? "Network error"));
    },
  );

  // toApiError handles direct api.raw.* callers (e.g. reports.download) where
  // tests may bypass the response interceptor. Method-level callers fall through
  // the `instanceof ApiError` short-circuit because the interceptor already
  // converted the error.
  function toApiError(err: unknown): ApiError {
    if (err instanceof ApiError) {
      return err;
    }
    const e = err as {
      response?: { status?: number; data?: unknown };
      message?: string;
    };
    const apiErr = apiErrorFromResponseData(e.response?.data);
    if (apiErr) {
      return apiErr;
    }
    if (e.response?.status === 401) {
      return new ApiError("UNAUTHORIZED", e.message ?? "Unauthorized");
    }
    return new ApiError("NETWORK_ERROR", e.message ?? "Network error");
  }

  return {
    raw: instance,
    async get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
      try {
        const resp = await instance.get<ApiEnvelope<T>>(url, { params });
        return unwrap<T>(resp);
      } catch (err) {
        throw toApiError(err);
      }
    },
    async post<T>(
      url: string,
      body?: unknown,
      config?: { headers?: Record<string, string> },
    ): Promise<T> {
      try {
        const resp = await instance.post<ApiEnvelope<T>>(url, body, {
          headers: config?.headers,
        });
        return unwrap<T>(resp);
      } catch (err) {
        throw toApiError(err);
      }
    },
    async patch<T>(url: string, body?: unknown): Promise<T> {
      try {
        const resp = await instance.patch<ApiEnvelope<T>>(url, body);
        return unwrap<T>(resp);
      } catch (err) {
        throw toApiError(err);
      }
    },
    async delete<T>(url: string): Promise<T> {
      try {
        const resp = await instance.delete<ApiEnvelope<T>>(url);
        return unwrap<T>(resp);
      } catch (err) {
        throw toApiError(err);
      }
    },
  };
}

let _api: Client | null = null;

function getApi(): Client {
  if (!_api) {
    _api = createClient();
  }
  return _api;
}

export const api: Client = new Proxy({} as Client, {
  get(_target, prop: keyof Client) {
    const instance = getApi();
    const value = instance[prop];
    // `raw` is an AxiosInstance — itself a callable function with method
    // properties (`raw.get`, `raw.post`, …). Binding it strips those methods,
    // so we must return the bare instance for `raw` and bind only the
    // method wrappers (`get`/`post`/`patch`/`delete`).
    if (prop === "raw") {
      return value;
    }
    if (typeof value === "function") {
      return (value as (...args: unknown[]) => unknown).bind(instance);
    }
    return value;
  },
});
