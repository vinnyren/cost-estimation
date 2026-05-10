import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
import FpEditor from "@/views/FpEditor.vue";
import { functionsApi } from "@/api/functions";
import { uploadsApi } from "@/api/uploads";

vi.mock("@/api/functions", () => ({
  functionsApi: {
    list: vi.fn().mockResolvedValue({ items: [] }),
    bulk: vi.fn(),
    patch: vi.fn(),
    snapshots: vi.fn(),
    restore: vi.fn(),
  },
}));

vi.mock("@/api/uploads", () => ({
  uploadsApi: { upload: vi.fn() },
}));

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: "/projects/:id/functions", component: FpEditor, name: "fp-editor" },
    {
      path: "/projects/:id/parameters",
      component: { template: "<div/>" },
      name: "param-manager",
    },
    {
      path: "/projects/:id/result",
      component: { template: "<div/>" },
      name: "result-view",
    },
  ],
});

describe("FpEditor", () => {
  beforeEach(async () => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    (functionsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    // Seed the in-memory router at a real route — otherwise the initial empty
    // path triggers a Vue Router "no match found" warning that shows up in
    // CI logs and makes real failures harder to spot.
    await router.push("/projects/p-1/functions");
    await router.isReady();
  });

  it("空表态显示 hero CTA：上传文档让 AI 写第一稿", async () => {
    const w = mount(FpEditor, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    expect(w.text()).toContain("上传文档让 AI 写第一稿");
  });

  it("加载失败时显示 ErrorBanner", async () => {
    (functionsApi.list as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("加载错"),
    );
    const w = mount(FpEditor, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    expect(w.find("[role='alert']").exists()).toBe(true);
    expect(w.text()).toContain("加载错");
  });

  it("有数据时显示功能点表（含 sourceLabel 渲染）", async () => {
    (functionsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: "f-1",
        project_id: "p-1",
        subsystem: "S1",
        l1_module: "M1",
        description: "d",
        category: "EI",
        complexity: "low",
        ufp: 4,
        reuse_level: "low",
        modify_type: "new",
        us: 4,
        source: "manual",
        version: 1,
      },
      {
        id: "f-2",
        project_id: "p-1",
        subsystem: "S2",
        l1_module: "M2",
        description: "d",
        category: "EO",
        complexity: "low",
        ufp: 5,
        reuse_level: "low",
        modify_type: "new",
        us: 5,
        source: "ai_extracted",
        version: 1,
      },
      {
        id: "f-3",
        project_id: "p-1",
        subsystem: "S3",
        l1_module: "M3",
        description: "d",
        category: "EQ",
        complexity: "low",
        ufp: 3,
        reuse_level: "low",
        modify_type: "new",
        us: 3,
        source: "allocator",
        version: 1,
      },
    ]);
    const w = mount(FpEditor, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    expect(w.text()).toContain("手工");
    expect(w.text()).toContain("AI 提取");
    expect(w.text()).toContain("预算倒推");
  });

  it("点击「参数管理」→ 路由跳 param-manager", async () => {
    const w = mount(FpEditor, {
      props: { projectId: "p-7" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    const paramBtn = w.findAll("button").find((b) => b.text() === "参数管理");
    await paramBtn!.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("param-manager");
    expect(router.currentRoute.value.params.id).toBe("p-7");
  });

  it("点击「计算 → 结果页」→ 路由跳 result-view", async () => {
    const w = mount(FpEditor, {
      props: { projectId: "p-9" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    const calcBtn = w.findAll("button").find((b) => b.text().includes("计算"));
    await calcBtn!.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("result-view");
    expect(router.currentRoute.value.params.id).toBe("p-9");
  });

  it("点击 hero CTA → 触发 file input click（pickFile）", async () => {
    const w = mount(FpEditor, {
      props: { projectId: "p-1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
      attachTo: document.body,
    });
    await flushPromises();
    const input = w.find("input[type='file']");
    expect(input.exists()).toBe(true);
    const clickSpy = vi.spyOn(input.element as HTMLInputElement, "click");
    const cta = w.find("[data-test='empty-cta']");
    if (cta.exists()) {
      await cta.trigger("click");
      expect(clickSpy).toHaveBeenCalled();
    } else {
      // Fallback: find any button containing 上传 text inside the empty state region
      const uploadBtn = w
        .findAll("button")
        .find((b) => b.text().includes("上传文档让 AI 写第一稿"));
      expect(uploadBtn).toBeDefined();
      await uploadBtn!.trigger("click");
      expect(clickSpy).toHaveBeenCalled();
    }
    w.unmount();
  });

  it("file input change 事件 → 调 uploadsApi.upload 并显示提示弹窗", async () => {
    (uploadsApi.upload as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      upload_id: 1,
      filename: "f.txt",
      size: 4,
    });
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});
    const w = mount(FpEditor, {
      props: { projectId: "p-5" },
      global: { plugins: [createPinia(), router, ElementPlus] },
      attachTo: document.body,
    });
    await flushPromises();
    const fileInput = w.find("input[type='file']").element as HTMLInputElement;
    const file = new File(["test"], "f.txt", { type: "text/plain" });
    Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
    await w.find("input[type='file']").trigger("change");
    await flushPromises();
    expect(uploadsApi.upload).toHaveBeenCalledWith("p-5", file);
    expect(alertSpy).toHaveBeenCalled();
    w.unmount();
  });

  it("历史版本下拉：点击拉 snapshots，再次点击关闭", async () => {
    (functionsApi.snapshots as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      { id: 2, version: 2, snapshot_at: "2026-05-11T01:00:00", reason: "bulk_write", fp_count: 3 },
      { id: 1, version: 1, snapshot_at: "2026-05-11T00:30:00", reason: "bulk_write", fp_count: 1 },
    ]);
    const w = mount(FpEditor, {
      props: { projectId: "p-h1" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    const histBtn = w.findAll("button").find((b) => b.text().includes("历史版本"))!;
    await histBtn.trigger("click");
    await flushPromises();
    expect(functionsApi.snapshots).toHaveBeenCalledWith("p-h1");
    expect(w.text()).toContain("v2");
    expect(w.text()).toContain("v1");
    expect(w.text()).toContain("3 FP");
    // 再次点击 → 关闭（不再调 snapshots）
    await histBtn.trigger("click");
    await flushPromises();
    expect(w.find("[role='dialog'][aria-label='功能点历史版本']").exists()).toBe(false);
  });

  it("历史版本：恢复按钮 confirm 后调 restore 并重新 load", async () => {
    (functionsApi.snapshots as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      { id: 1, version: 1, snapshot_at: "2026-05-11T00:30:00", reason: "bulk_write", fp_count: 1 },
    ]);
    (functionsApi.restore as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      restored_version: 1,
      fp_count: 1,
    });
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const w = mount(FpEditor, {
      props: { projectId: "p-h2" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    const histBtn = w.findAll("button").find((b) => b.text().includes("历史版本"))!;
    await histBtn.trigger("click");
    await flushPromises();
    const restoreBtn = w.findAll("button").find((b) => b.text().includes("恢复"))!;
    await restoreBtn.trigger("click");
    await flushPromises();
    expect(confirmSpy).toHaveBeenCalled();
    expect(functionsApi.restore).toHaveBeenCalledWith("p-h2", 1);
    // 恢复后会再调 list（一次 onMounted + 一次 reload）
    expect(functionsApi.list).toHaveBeenCalledTimes(2);
    confirmSpy.mockRestore();
  });

  it("历史版本：confirm 取消则不调 restore", async () => {
    (functionsApi.snapshots as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      { id: 1, version: 1, snapshot_at: "2026-05-11T00:30:00", reason: null, fp_count: 1 },
    ]);
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const w = mount(FpEditor, {
      props: { projectId: "p-h3" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    await w.findAll("button").find((b) => b.text().includes("历史版本"))!.trigger("click");
    await flushPromises();
    await w.findAll("button").find((b) => b.text().includes("恢复"))!.trigger("click");
    await flushPromises();
    expect(functionsApi.restore).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });
});
