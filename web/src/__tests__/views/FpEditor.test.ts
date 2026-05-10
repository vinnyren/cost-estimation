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
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    (functionsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ items: [] });
  });

  it("空表态显示 hero CTA：上传文档让 AI 写第一稿", async () => {
    const w = mount(FpEditor, {
      props: { projectId: 1 },
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
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    expect(w.find("[role='alert']").exists()).toBe(true);
    expect(w.text()).toContain("加载错");
  });

  it("有数据时显示功能点表（含 sourceLabel 渲染）", async () => {
    (functionsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 1,
          project_id: 1,
          subsystem: "S1",
          module_l1: "M1",
          description: "d",
          category: "EI",
          ufp: 4,
          reuse_ratio: 0,
          modify_ratio: 0,
          us: 4,
          source: "manual",
          version: 1,
        },
        {
          id: 2,
          project_id: 1,
          subsystem: "S2",
          module_l1: "M2",
          description: "d",
          category: "EO",
          ufp: 5,
          reuse_ratio: 0,
          modify_ratio: 0,
          us: 5,
          source: "ai_extracted",
          version: 1,
        },
        {
          id: 3,
          project_id: 1,
          subsystem: "S3",
          module_l1: "M3",
          description: "d",
          category: "EQ",
          ufp: 3,
          reuse_ratio: 0,
          modify_ratio: 0,
          us: 3,
          source: "allocator",
          version: 1,
        },
      ],
    });
    const w = mount(FpEditor, {
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    expect(w.text()).toContain("手工");
    expect(w.text()).toContain("AI 提取");
    expect(w.text()).toContain("预算倒推");
  });

  it("点击「参数管理」→ 路由跳 param-manager", async () => {
    const w = mount(FpEditor, {
      props: { projectId: 7 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    const paramBtn = w.findAll("button").find((b) => b.text() === "参数管理");
    await paramBtn!.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("param-manager");
    expect(router.currentRoute.value.params.id).toBe("7");
  });

  it("点击「计算 → 结果页」→ 路由跳 result-view", async () => {
    const w = mount(FpEditor, {
      props: { projectId: 9 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    const calcBtn = w.findAll("button").find((b) => b.text().includes("计算"));
    await calcBtn!.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("result-view");
    expect(router.currentRoute.value.params.id).toBe("9");
  });

  it("点击 hero CTA → 触发 file input click（pickFile）", async () => {
    const w = mount(FpEditor, {
      props: { projectId: 1 },
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
      props: { projectId: 5 },
      global: { plugins: [createPinia(), router, ElementPlus] },
      attachTo: document.body,
    });
    await flushPromises();
    const fileInput = w.find("input[type='file']").element as HTMLInputElement;
    const file = new File(["test"], "f.txt", { type: "text/plain" });
    Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
    await w.find("input[type='file']").trigger("change");
    await flushPromises();
    expect(uploadsApi.upload).toHaveBeenCalledWith(5, file);
    expect(alertSpy).toHaveBeenCalled();
    w.unmount();
  });
});
