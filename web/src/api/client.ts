import axios, { type AxiosInstance, type AxiosResponse } from "axios";
import type { ApiEnvelope } from "./types";

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
  return sessionStorage.getItem("auth_token") ?? "";
}

export interface Client {
  get<T>(url: string, params?: Record<string, unknown>): Promise<T>;
  post<T>(url: string, body?: unknown, config?: { headers?: Record<string, string> }): Promise<T>;
  patch<T>(url: string, body?: unknown): Promise<T>;
  delete<T>(url: string): Promise<T>;
  raw: AxiosInstance;
}

export function createClient(): Client {
  const instance = axios.create({
    baseURL: "",
    timeout: 30_000,
    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
  });

  instance.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
      config.headers = config.headers ?? {};
      (config.headers as Record<string, string>)["X-Auth-Token"] = token;
    }
    return config;
  });

  instance.interceptors.response.use(
    (resp) => resp,
    (err: unknown) => {
      const e = err as {
        response?: { data?: { error?: { code?: string; message?: string; details?: Record<string, unknown> } } };
        message?: string;
      };
      const errorEnvelope = e.response?.data?.error;
      if (errorEnvelope?.code) {
        return Promise.reject(
          new ApiError(errorEnvelope.code, errorEnvelope.message ?? "", errorEnvelope.details),
        );
      }
      return Promise.reject(new ApiError("NETWORK_ERROR", e.message ?? "Network error"));
    },
  );

  function toApiError(err: unknown): ApiError {
    if (err instanceof ApiError) {
      return err;
    }
    const e = err as {
      response?: {
        status?: number;
        data?: {
          error?: { code?: string; message?: string; details?: Record<string, unknown> };
        };
      };
      message?: string;
    };
    const errorEnvelope = e.response?.data?.error;
    if (errorEnvelope?.code) {
      return new ApiError(
        errorEnvelope.code,
        errorEnvelope.message ?? "",
        errorEnvelope.details,
      );
    }
    if (e.response?.status === 401) {
      return new ApiError("UNAUTHORIZED", e.message ?? "Unauthorized");
    }
    return new ApiError("NETWORK_ERROR", e.message ?? "Network error");
  }

  return {
    raw: instance,
    async get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
      const headers = { "X-Auth-Token": getToken() };
      try {
        const resp = await instance.get<ApiEnvelope<T>>(url, { params, headers });
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
      const headers = { "X-Auth-Token": getToken(), ...(config?.headers ?? {}) };
      try {
        const resp = await instance.post<ApiEnvelope<T>>(url, body, { headers });
        return unwrap<T>(resp);
      } catch (err) {
        throw toApiError(err);
      }
    },
    async patch<T>(url: string, body?: unknown): Promise<T> {
      const headers = { "X-Auth-Token": getToken() };
      try {
        const resp = await instance.patch<ApiEnvelope<T>>(url, body, { headers });
        return unwrap<T>(resp);
      } catch (err) {
        throw toApiError(err);
      }
    },
    async delete<T>(url: string): Promise<T> {
      const headers = { "X-Auth-Token": getToken() };
      try {
        const resp = await instance.delete<ApiEnvelope<T>>(url, { headers });
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
    if (typeof value === "function") {
      return (value as (...args: unknown[]) => unknown).bind(instance);
    }
    return value;
  },
});
