import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
import FpEditor from "@/views/FpEditor.vue";

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
  routes: [{ path: "/projects/:id/functions", component: FpEditor, name: "fp-editor" }],
});

describe("FpEditor", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("空表态显示 hero CTA：上传文档让 AI 写第一稿", async () => {
    const w = mount(FpEditor, {
      props: { projectId: 1 },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    expect(w.text()).toContain("上传文档让 AI 写第一稿");
  });
});
