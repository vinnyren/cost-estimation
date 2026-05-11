// v2.0 T8 — API client for new {success,data,meta} envelopes.
//
// projectsApi.query/copy, snapshotsApi, and auditApi go through api.raw
// (bypassing unwrap()) because the new backend endpoints emit the
// {success, data, error, meta?} envelope, not the legacy {ok, data} envelope
// that unwrap() understands. The legacy projectsApi.list() stays as-is and
// will be migrated to .query() in T20 (ProjectList toolbar).
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    raw: {
      get: vi.fn(),
      post: vi.fn(),
      delete: vi.fn(),
    },
  },
  ApiError: class ApiError extends Error {},
}));

import { projectsApi } from "@/api/projects";
import { snapshotsApi } from "@/api/snapshots";
import { auditApi } from "@/api/audit";
import { api } from "@/api/client";

type RawGet = ReturnType<typeof vi.fn>;
const rawGet = () => api.raw.get as unknown as RawGet;
const rawPost = () => api.raw.post as unknown as RawGet;
const rawDelete = () => api.raw.delete as unknown as RawGet;

beforeEach(() => {
  vi.clearAllMocks();
});

describe("projectsApi.query (new {success,data,meta} envelope)", () => {
  it("passes filter / sort / page params and returns data + meta", async () => {
    rawGet().mockResolvedValue({
      data: { success: true, data: [{ id: "p1" }], meta: { total: 7, page: 2, size: 20 } },
    });

    const result = await projectsApi.query({
      q: "智慧",
      city: "北京",
      page: 2,
      size: 20,
    });

    expect(rawGet()).toHaveBeenCalledTimes(1);
    const url = rawGet().mock.calls[0][0] as string;
    expect(url.startsWith("/api/projects?")).toBe(true);
    expect(url).toContain("q=%E6%99%BA%E6%85%A7");
    expect(url).toContain("city=%E5%8C%97%E4%BA%AC");
    expect(url).toContain("page=2");
    expect(url).toContain("size=20");
    expect(result.data).toEqual([{ id: "p1" }]);
    expect(result.meta).toEqual({ total: 7, page: 2, size: 20 });
  });

  it("omits undefined / empty params from the query string", async () => {
    rawGet().mockResolvedValue({
      data: { success: true, data: [], meta: { total: 0, page: 1, size: 50 } },
    });
    await projectsApi.query({ q: "", city: undefined, sort: "name" });
    const url = rawGet().mock.calls[0][0] as string;
    expect(url).not.toContain("q=");
    expect(url).not.toContain("city=");
    expect(url).toContain("sort=name");
  });

  it("omits the query string entirely when no options are given", async () => {
    rawGet().mockResolvedValue({
      data: { success: true, data: [], meta: { total: 0, page: 1, size: 50 } },
    });
    await projectsApi.query();
    expect(rawGet().mock.calls[0][0]).toBe("/api/projects");
  });
});

describe("projectsApi.copy", () => {
  it("POSTs the new name to /api/projects/{id}/copy", async () => {
    rawPost().mockResolvedValue({
      data: { success: true, data: { id: "new-id", name: "新名" }, error: null },
    });
    const result = await projectsApi.copy("src-id", "新名");
    expect(rawPost()).toHaveBeenCalledWith("/api/projects/src-id/copy", { name: "新名" });
    expect(result).toEqual({ id: "new-id", name: "新名" });
  });
});

describe("snapshotsApi", () => {
  it("list passes scope as query param", async () => {
    rawGet().mockResolvedValue({
      data: { success: true, data: [], error: null },
    });
    await snapshotsApi.list("global");
    expect(rawGet().mock.calls[0][0]).toBe("/api/params/snapshots?scope=global");
  });

  it("list with no scope omits the query string", async () => {
    rawGet().mockResolvedValue({
      data: { success: true, data: [], error: null },
    });
    await snapshotsApi.list();
    expect(rawGet().mock.calls[0][0]).toBe("/api/params/snapshots");
  });

  it("create POSTs scope + label", async () => {
    rawPost().mockResolvedValue({
      data: { success: true, data: { id: 1, scope: "global", label: "x", created_at: "t" }, error: null },
    });
    const out = await snapshotsApi.create({ scope: "global", label: "x" });
    expect(rawPost()).toHaveBeenCalledWith("/api/params/snapshots", { scope: "global", label: "x" });
    expect(out.id).toBe(1);
  });

  it("restore POSTs to /snapshots/{id}/restore", async () => {
    rawPost().mockResolvedValue({
      data: { success: true, data: { restored: 3 }, error: null },
    });
    await snapshotsApi.restore(42);
    expect(rawPost()).toHaveBeenCalledWith("/api/params/snapshots/42/restore");
  });

  it("remove DELETEs /snapshots/{id}", async () => {
    rawDelete().mockResolvedValue({ status: 204, data: "" });
    await snapshotsApi.remove(7);
    expect(rawDelete()).toHaveBeenCalledWith("/api/params/snapshots/7");
  });
});

describe("auditApi", () => {
  it("list passes limit + before_id as cursor pagination params", async () => {
    rawGet().mockResolvedValue({
      data: { success: true, data: [], error: null },
    });
    await auditApi.list("p1", { limit: 50, beforeId: 100 });
    const url = rawGet().mock.calls[0][0] as string;
    expect(url.startsWith("/api/projects/p1/audit?")).toBe(true);
    expect(url).toContain("limit=50");
    expect(url).toContain("before_id=100");
  });

  it("list without options hits the bare endpoint", async () => {
    rawGet().mockResolvedValue({
      data: { success: true, data: [], error: null },
    });
    await auditApi.list("p2");
    expect(rawGet().mock.calls[0][0]).toBe("/api/projects/p2/audit");
  });
});
