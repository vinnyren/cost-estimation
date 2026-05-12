import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  ApiError: class ApiError extends Error {},
}));

import { uploadsApi, type UploadRecord } from "@/api/uploads";
import { api } from "@/api/client";

describe("uploadsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("upload 调 POST /api/projects/:id/uploads 且 body 是 FormData（含 file 字段）", async () => {
    const reply = { upload_id: 1, filename: "spec.txt", size: 4 };
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(reply);
    const file = new File(["abcd"], "spec.txt", { type: "text/plain" });

    const result = await uploadsApi.upload("p-123", file);

    expect(api.post).toHaveBeenCalledTimes(1);
    const [url, body] = (api.post as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe("/api/projects/p-123/uploads");
    expect(body).toBeInstanceOf(FormData);
    // FormData.get returns File-like value; verify the field exists
    const sent = (body as FormData).get("file");
    expect(sent).toBeTruthy();
    expect((sent as File).name).toBe("spec.txt");
    expect(result).toEqual(reply);
  });
});

describe("uploadsApi.list (v2.5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls /api/projects/{pid}/uploads and returns data array", async () => {
    const mockData: UploadRecord[] = [
      {
        id: 1,
        project_id: "p-1",
        filename: "a.txt",
        size: 100,
        filetype: "text/plain",
        uploaded_at: "2026-05-12T00:00:00Z",
        parsed_text_path: "p-1/1__a.txt",
      },
    ];
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockData);

    const result = await uploadsApi.list("p-1");

    expect(api.get).toHaveBeenCalledTimes(1);
    expect(api.get).toHaveBeenCalledWith("/api/projects/p-1/uploads");
    expect(result).toHaveLength(1);
    expect(result[0].filename).toBe("a.txt");
  });

  it("URL-encodes project IDs with special characters", async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);

    await uploadsApi.list("p/special id");

    expect(api.get).toHaveBeenCalledWith(
      "/api/projects/p%2Fspecial%20id/uploads"
    );
  });
});

describe("uploadsApi.remove (v2.5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls DELETE /api/projects/{pid}/uploads/{id}", async () => {
    (api.delete as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);

    await uploadsApi.remove("p-1", 42);

    expect(api.delete).toHaveBeenCalledTimes(1);
    expect(api.delete).toHaveBeenCalledWith("/api/projects/p-1/uploads/42");
  });

  it("URL-encodes project ID in delete path", async () => {
    (api.delete as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);

    await uploadsApi.remove("p/special", 7);

    expect(api.delete).toHaveBeenCalledWith("/api/projects/p%2Fspecial/uploads/7");
  });
});
