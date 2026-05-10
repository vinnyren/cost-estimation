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

import { uploadsApi } from "@/api/uploads";
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
