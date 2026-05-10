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

  it("api Proxy 懒初始化 + 方法绑定", async () => {
    // The exported `api` Proxy lazily creates a single client on first access
    // and binds methods to that instance. We verify the Proxy resolves to a
    // working client by importing it and invoking a method.
    const get = vi.fn().mockResolvedValue({ data: { ok: true, data: "ok" } });
    (axios.create as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      post: vi.fn(),
      get,
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    });
    // Re-import a fresh module so _api singleton is reset
    vi.resetModules();
    const { api } = await import("@/api/client");
    const result = await api.get<string>("/api/x");
    expect(result).toBe("ok");
    // Access raw — also a Proxy trap path
    expect(api.raw).toBeDefined();
  });

  it("post/patch/delete 解封成功响应 → 返回 data", async () => {
    const stub = vi.fn().mockResolvedValue({ data: { ok: true, data: { id: 1 } } });
    (axios.create as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      post: stub,
      get: vi.fn(),
      patch: stub,
      delete: stub,
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    });
    const client = createClient();
    expect(await client.post("/api/x", { a: 1 })).toEqual({ id: 1 });
    expect(await client.patch("/api/x", { a: 2 })).toEqual({ id: 1 });
    expect(await client.delete("/api/x")).toEqual({ id: 1 });
  });

  it("post 失败 → throw ApiError", async () => {
    const err = { response: { data: { error: { code: "BAD", message: "no" } } } };
    const post = vi.fn().mockRejectedValue(err);
    (axios.create as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      post,
      get: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    });
    const client = createClient();
    await expect(client.post("/api/x", {})).rejects.toBeInstanceOf(ApiError);
  });

  it("malformed envelope (非对象 data) → throw INVALID_RESPONSE", async () => {
    const get = vi.fn().mockResolvedValue({ data: null });
    (axios.create as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      post: vi.fn(),
      get,
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    });
    const client = createClient();
    await expect(client.get("/api/x")).rejects.toMatchObject({ code: "INVALID_RESPONSE" });
  });

  it("无 token 时不注入 X-Auth-Token 请求头", () => {
    sessionStorage.clear();
    const requestUse = vi.fn();
    (axios.create as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      post: vi.fn(),
      get: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: requestUse }, response: { use: vi.fn() } },
    });
    createClient();
    const interceptor = requestUse.mock.calls[0][0] as (c: {
      headers?: Record<string, string>;
    }) => { headers?: Record<string, string> };
    const inputConfig = { headers: { "X-Requested-With": "XMLHttpRequest" } };
    const result = interceptor(inputConfig);
    // Should be the same config when no token is present
    expect(result).toBe(inputConfig);
    expect(result.headers?.["X-Auth-Token"]).toBeUndefined();
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

describe("api Proxy raw passthrough (regression)", () => {
  // Regression for a production bug found in e2e:
  // The Proxy used to apply `.bind(instance)` to every method-typed value,
  // which silently stripped `.get`/`.post`/etc. method properties off the
  // AxiosInstance returned by `api.raw` (an AxiosInstance is a callable
  // function with method properties). Direct callers like `reports.download`
  // (which uses `api.raw.get(url, { responseType: 'blob' })`) then crashed at
  // runtime with `api.raw.get is not a function`. The fix short-circuits
  // `prop === "raw"` to return the bare instance.
  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem("auth_token", "test-token-123");
    vi.resetAllMocks();
    vi.resetModules();
  });

  it("api.raw 透传 AxiosInstance（保留 .get/.post 等方法属性，未被 .bind() 剥离）", async () => {
    // Construct a callable function that also carries method properties — this
    // mirrors a real AxiosInstance shape (Axios returns a function with
    // `.get`/`.post`/`.interceptors` attached).
    const mockGet = vi.fn().mockResolvedValue({ data: new Blob(["x"]) });
    const mockInstance = function placeholderInstance() {
      /* AxiosInstance is callable; tests don't invoke it directly */
    } as unknown as {
      (): unknown;
      get: ReturnType<typeof vi.fn>;
      post: ReturnType<typeof vi.fn>;
      patch: ReturnType<typeof vi.fn>;
      delete: ReturnType<typeof vi.fn>;
      interceptors: {
        request: { use: ReturnType<typeof vi.fn> };
        response: { use: ReturnType<typeof vi.fn> };
      };
    };
    mockInstance.get = mockGet;
    mockInstance.post = vi.fn();
    mockInstance.patch = vi.fn();
    mockInstance.delete = vi.fn();
    mockInstance.interceptors = {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    };
    (axios.create as unknown as ReturnType<typeof vi.fn>).mockReturnValue(mockInstance);

    // Re-import so the module-scoped `_api` singleton is reset and the Proxy
    // creates a fresh client backed by our mock instance.
    const { api } = await import("@/api/client");

    // raw should be a callable whose method properties are still attached
    // (i.e. not bound away).
    expect(typeof api.raw).toBe("function");
    expect(typeof api.raw.get).toBe("function");
    expect(typeof api.raw.post).toBe("function");
    expect(typeof api.raw.patch).toBe("function");
    expect(typeof api.raw.delete).toBe("function");

    // And the methods route to the mock — confirms raw is the same instance,
    // not a stripped/wrapped clone.
    const r = await api.raw.get("/test");
    expect(mockGet).toHaveBeenCalledWith("/test");
    expect(r.data).toBeInstanceOf(Blob);
  });
});
