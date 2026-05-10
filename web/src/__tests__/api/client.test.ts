import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import { createClient, ApiError } from "@/api/client";

vi.mock("axios");

describe("API client", () => {
  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem("auth_token", "test-token-123");
    vi.resetAllMocks();
  });

  it("注入 X-Auth-Token 请求头（拦截器单一注入点）", () => {
    // The request interceptor is the single token-injection point. We verify
    // the registered callback injects X-Auth-Token immutably, since the axios
    // mock's interceptors.request.use is a vi.fn() that never invokes it.
    const requestUse = vi.fn();
    (axios.create as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      post: vi.fn(),
      get: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: requestUse }, response: { use: vi.fn() } },
    });
    createClient();
    expect(requestUse).toHaveBeenCalledTimes(1);
    const interceptor = requestUse.mock.calls[0][0] as (c: {
      headers?: Record<string, string>;
    }) => { headers?: Record<string, string> };
    const inputConfig = { headers: { "X-Requested-With": "XMLHttpRequest" } };
    const result = interceptor(inputConfig);
    expect(result.headers).toMatchObject({
      "X-Requested-With": "XMLHttpRequest",
      "X-Auth-Token": "test-token-123",
    });
    // Immutability: the original config must not have been mutated.
    expect(inputConfig.headers).toEqual({ "X-Requested-With": "XMLHttpRequest" });
    expect(result).not.toBe(inputConfig);
  });

  it("解封成功响应：{ok:true,data} → data", async () => {
    const get = vi.fn().mockResolvedValue({ data: { ok: true, data: { items: [1, 2] } } });
    (axios.create as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      post: vi.fn(),
      get,
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    });
    const client = createClient();
    const data = await client.get("/api/projects");
    expect(data).toEqual({ items: [1, 2] });
  });

  it("解封错误响应：{ok:false,error} → throw ApiError", async () => {
    const get = vi.fn().mockResolvedValue({
      data: {
        ok: false,
        error: { code: "INVALID_PARAM", message: "城市无效", details: { field: "city" } },
      },
    });
    (axios.create as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      post: vi.fn(),
      get,
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    });
    const client = createClient();
    await expect(client.get("/api/projects")).rejects.toMatchObject({
      code: "INVALID_PARAM",
      message: "城市无效",
      details: { field: "city" },
    });
  });

  it("HTTP 401 → throw ApiError(UNAUTHORIZED)", async () => {
    const err = new Error("Request failed") as Error & {
      response?: { status: number; data: { error: { code: string; message: string } } };
    };
    err.response = {
      status: 401,
      data: { error: { code: "UNAUTHORIZED", message: "Invalid token" } },
    };
    const get = vi.fn().mockRejectedValue(err);
    (axios.create as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      post: vi.fn(),
      get,
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    });
    const client = createClient();
    await expect(client.get("/api/projects")).rejects.toBeInstanceOf(ApiError);
  });
});
