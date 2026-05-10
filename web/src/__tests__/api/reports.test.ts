import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("@/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    raw: { get: vi.fn() },
  },
  ApiError: class ApiError extends Error {},
}));

import { reportsApi } from "@/api/reports";
import { api } from "@/api/client";

describe("reportsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("excelUrl 拼接路径 /api/reports/excel/:id", () => {
    expect(reportsApi.excelUrl("p-42")).toBe("/api/reports/excel/p-42");
  });

  it("download 走 api.raw.get blob、触发 anchor.click 并清理 ObjectURL", async () => {
    (api.raw.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: new Blob(["test-content"]),
    });
    const mockClick = vi.fn();
    const fakeAnchor: { click: () => void; href: string; download: string } = {
      click: mockClick,
      href: "",
      download: "",
    };
    const createElementSpy = vi
      .spyOn(document, "createElement")
      .mockImplementation(((tag: string) => {
        if (tag === "a") return fakeAnchor as unknown as HTMLAnchorElement;
        // Fallback to a minimal stand-in for any other tag (none expected here).
        return { click: vi.fn(), href: "", download: "" } as unknown as HTMLAnchorElement;
      }) as typeof document.createElement);
    const createUrlSpy = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:mock");
    const revokeUrlSpy = vi.spyOn(URL, "revokeObjectURL").mockReturnValue(undefined);

    await reportsApi.download("p-7", "out.xlsx");

    expect(api.raw.get).toHaveBeenCalledWith("/api/reports/excel/p-7", { responseType: "blob" });
    expect(createElementSpy).toHaveBeenCalledWith("a");
    expect(createUrlSpy).toHaveBeenCalledTimes(1);
    expect(fakeAnchor.href).toBe("blob:mock");
    expect(fakeAnchor.download).toBe("out.xlsx");
    expect(mockClick).toHaveBeenCalledTimes(1);
    expect(revokeUrlSpy).toHaveBeenCalledWith("blob:mock");
  });

  it("download 默认文件名 = 造价报告.xlsx", async () => {
    (api.raw.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: new Blob(["x"]),
    });
    const fakeAnchor: { click: () => void; href: string; download: string } = {
      click: vi.fn(),
      href: "",
      download: "",
    };
    vi.spyOn(document, "createElement").mockImplementation(((tag: string) => {
      if (tag === "a") return fakeAnchor as unknown as HTMLAnchorElement;
      return { click: vi.fn(), href: "", download: "" } as unknown as HTMLAnchorElement;
    }) as typeof document.createElement);
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock");
    vi.spyOn(URL, "revokeObjectURL").mockReturnValue(undefined);

    await reportsApi.download("p-1");
    expect(fakeAnchor.download).toBe("造价报告.xlsx");
  });
});
