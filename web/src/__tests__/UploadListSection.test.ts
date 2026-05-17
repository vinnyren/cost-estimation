// web/src/__tests__/UploadListSection.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import UploadListSection from "@/components/fp/UploadListSection.vue";

vi.mock("@/api/uploads", () => ({
  uploadsApi: {
    list: vi.fn(),
    remove: vi.fn(),
  },
}));
import { uploadsApi } from "@/api/uploads";

describe("UploadListSection (v2.5)", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it("renders nothing when list is empty", async () => {
    (uploadsApi.list as any).mockResolvedValue([]);
    const w = mount(UploadListSection, { props: { projectId: "p-1" } });
    await flushPromises();
    expect(w.find(".upload-section").exists()).toBe(false);
  });

  it("renders inline section with rows + fmtSize KB", async () => {
    (uploadsApi.list as any).mockResolvedValue([
      { id: 1, project_id: "p-1", filename: "doc.pdf", size: 2048, filetype: "pdf",
        uploaded_at: "2026-05-12T10:30:00Z", parsed_text_path: null },
    ]);
    const w = mount(UploadListSection, { props: { projectId: "p-1" } });
    await flushPromises();
    expect(w.find(".upload-section").exists()).toBe(true);
    expect(w.text()).toContain("已上传文件");
    expect(w.text()).toContain("doc.pdf");
    expect(w.text()).toContain("2.0 KB");
  });

  it("emits refreshed with count after load", async () => {
    (uploadsApi.list as any).mockResolvedValue([
      { id: 1, project_id: "p-1", filename: "a.txt", size: 10, filetype: "txt",
        uploaded_at: "2026-05-12T10:00:00Z", parsed_text_path: null },
      { id: 2, project_id: "p-1", filename: "b.txt", size: 20, filetype: "txt",
        uploaded_at: "2026-05-12T10:01:00Z", parsed_text_path: null },
    ]);
    const w = mount(UploadListSection, { props: { projectId: "p-1" } });
    await flushPromises();
    expect(w.emitted("refreshed")?.[0]).toEqual([2]);
  });

  it("calls remove + reloads when 删除 clicked and confirmed", async () => {
    (uploadsApi.list as any)
      .mockResolvedValueOnce([
        { id: 7, project_id: "p-1", filename: "x.txt", size: 5, filetype: "txt",
          uploaded_at: "2026-05-12T10:00:00Z", parsed_text_path: null },
      ])
      .mockResolvedValueOnce([]);
    (uploadsApi.remove as any).mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    const w = mount(UploadListSection, { props: { projectId: "p-1" } });
    await flushPromises();
    const delBtn = w.findAll("button").find((b) => b.text() === "删除");
    await delBtn!.trigger("click");
    await flushPromises();

    expect(uploadsApi.remove).toHaveBeenCalledWith("p-1", 7);
    expect(w.find(".upload-section").exists()).toBe(false);
  });
});
