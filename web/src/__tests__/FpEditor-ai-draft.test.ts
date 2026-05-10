// Task 22 — GAP-A frontend: claude_draft 高亮 + AI Plugin hint
//
// 上传完成后告知用户用 /cost 让 Claude Code 写 FP；当 functions.source =
// 'claude_draft' 时，行需带 data-source、ai-draft class、以及 "AI 草稿" 徽标，
// 方便审核时一眼分辨出 AI 写的草稿与手工/导入数据。
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ElementPlus from "element-plus";
import FpEditor from "@/views/FpEditor.vue";
import { functionsApi } from "@/api/functions";

vi.mock("@/api/functions", () => ({
  functionsApi: {
    list: vi.fn(),
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

describe("FpEditor — claude_draft 高亮 (GAP-A)", () => {
  beforeEach(async () => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    await router.push("/projects/p-ai/functions");
    await router.isReady();
  });

  it("source=claude_draft 的行带 data-source + ai-draft class + 'AI 草稿' 徽标", async () => {
    (functionsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: "f-m",
        project_id: "p-ai",
        subsystem: "S1",
        l1_module: "M1",
        category: "EI",
        complexity: "low",
        ufp: 3,
        us: 3,
        source: "manual",
        version: 1,
      },
      {
        id: "f-ai",
        project_id: "p-ai",
        subsystem: "S2",
        l1_module: "M2",
        category: "EI",
        complexity: "low",
        ufp: 3,
        us: 3,
        source: "claude_draft",
        version: 1,
      },
    ]);
    const w = mount(FpEditor, {
      props: { projectId: "p-ai" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();

    const aiRow = w.find('[data-source="claude_draft"]');
    expect(aiRow.exists()).toBe(true);
    expect(aiRow.classes()).toContain("ai-draft");
    expect(aiRow.text()).toContain("AI 草稿");

    // manual 行不应该带 ai-draft class
    const manualRow = w.find('[data-source="manual"]');
    expect(manualRow.exists()).toBe(true);
    expect(manualRow.classes()).not.toContain("ai-draft");
  });

  it("sourceLabel 渲染 claude_draft 时显示「AI 草稿」", async () => {
    (functionsApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: "f-ai",
        project_id: "p-ai",
        subsystem: "S",
        l1_module: "M",
        category: "EI",
        complexity: "low",
        ufp: 3,
        us: 3,
        source: "claude_draft",
        version: 1,
      },
    ]);
    const w = mount(FpEditor, {
      props: { projectId: "p-ai" },
      global: { plugins: [createPinia(), router, ElementPlus] },
    });
    await flushPromises();
    expect(w.text()).toContain("AI 草稿");
  });
});
