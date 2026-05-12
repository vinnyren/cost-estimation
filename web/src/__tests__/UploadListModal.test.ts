// web/src/__tests__/UploadListModal.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import UploadListModal from "@/components/fp/UploadListModal.vue";

vi.mock("@/api/uploads", () => ({
  uploadsApi: {
    list: vi.fn(),
    remove: vi.fn(),
  },
}));
import { uploadsApi } from "@/api/uploads";

describe("UploadListModal", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it("renders empty state when list is empty", async () => {
    (uploadsApi.list as any).mockResolvedValue([]);
    const w = mount(UploadListModal, { props: { open: true, projectId: "p-1" } });
    await flushPromises();
    expect(w.text()).toContain("暂无上传文件");
  });

  it("renders rows + fmtSize KB", async () => {
    (uploadsApi.list as any).mockResolvedValue([
      { id: 1, project_id: "p-1", filename: "doc.pdf", size: 2048, filetype: "pdf",
        uploaded_at: "2026-05-12T10:30:00Z", parsed_text_path: null },
    ]);
    const w = mount(UploadListModal, { props: { open: true, projectId: "p-1" } });
    await flushPromises();
    expect(w.text()).toContain("doc.pdf");
    expect(w.text()).toContain("2.0 KB");
  });

  it("emits update:open false on close", async () => {
    (uploadsApi.list as any).mockResolvedValue([]);
    const w = mount(UploadListModal, { props: { open: true, projectId: "p-1" } });
    await flushPromises();
    const closeBtn = w.findAll("button").find((b) => b.text() === "关闭");
    await closeBtn!.trigger("click");
    expect(w.emitted("update:open")?.[0]).toEqual([false]);
  });
});
