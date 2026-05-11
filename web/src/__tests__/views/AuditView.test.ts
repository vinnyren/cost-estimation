// v2.2 T28 — AuditView (timeline 重做) test coverage.
//
// Verifies that the audit timeline:
//   - calls auditApi.list with the route's project id on mount;
//   - translates action codes to human labels via AuditTimeline ACTION_LABELS;
//   - falls back to the raw code for unknown actions;
//   - renders the empty state when the server returns no entries;
//   - paginates via "加载更多" (passes beforeId = oldest visible id).
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import AuditView from "@/views/AuditView.vue";

vi.mock("@/api/audit", () => ({
  auditApi: { list: vi.fn() },
}));

import { auditApi } from "@/api/audit";

type ListMock = ReturnType<typeof vi.fn>;
const listMock = () => auditApi.list as unknown as ListMock;

const entry = (overrides: Record<string, unknown> = {}) => ({
  id: 1,
  project_id: "p1",
  ts: "2026-05-11T08:30:00Z",
  actor: "user-a",
  action: "project.create",
  target: "p1",
  diff_json: null,
  ...overrides,
});

const mountAt = async (path = "/projects/p1/audit") => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/projects/:id/audit", component: AuditView, name: "project-audit" },
      { path: "/projects/:id/functions", component: { template: "<div/>" }, name: "fp-editor" },
    ],
  });
  await router.push(path);
  await router.isReady();
  return mount(AuditView, { global: { plugins: [router] } });
};

describe("AuditView", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("挂载时用 route 的 projectId 调 auditApi.list", async () => {
    listMock().mockResolvedValue([]);
    await mountAt("/projects/p1/audit");
    await flushPromises();
    expect(auditApi.list).toHaveBeenCalledWith("p1", { limit: 50, beforeId: undefined });
  });

  it("渲染审计条目并翻译 action 标签", async () => {
    listMock().mockResolvedValue([entry({ id: 1, action: "project.create" })]);
    const w = await mountAt();
    await flushPromises();
    // v2.2 timeline: each entry renders a .tl-item instead of audit-row
    expect(w.findAll(".tl-item").length).toBe(1);
    expect(w.text()).toContain("创建项目");
  });

  it("未知 action 回退到原始 code", async () => {
    listMock().mockResolvedValue([entry({ id: 2, action: "weird.unknown.event" })]);
    const w = await mountAt();
    await flushPromises();
    expect(w.text()).toContain("weird.unknown.event");
  });

  it("空数据时显示「暂无审计记录」", async () => {
    listMock().mockResolvedValue([]);
    const w = await mountAt();
    await flushPromises();
    // v2.2 timeline: empty state rendered as text in a card div
    expect(w.text()).toContain("暂无审计事件");
  });

  it("满页时显示「加载更多」按钮，点击后用最末 id 翻页", async () => {
    const firstPage = Array.from({ length: 50 }, (_, i) =>
      entry({ id: 100 - i, action: "fp.update" }),
    );
    const olderPage = [entry({ id: 50, action: "project.create" })];
    listMock()
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce(olderPage);

    const w = await mountAt();
    await flushPromises();
    // v2.2 timeline: load-more button has class btn-ghost
    const more = w.find("button.btn-ghost");
    expect(more.exists()).toBe(true);
    await more.trigger("click");
    await flushPromises();

    // Last row in firstPage has id 100 - 49 = 51 → beforeId should be 51.
    expect(auditApi.list).toHaveBeenLastCalledWith("p1", { limit: 50, beforeId: 51 });
    // Appends rather than replaces.
    expect(w.findAll(".tl-item").length).toBe(51);
  });

  it("少于一页时不显示「加载更多」按钮", async () => {
    listMock().mockResolvedValue([entry()]);
    const w = await mountAt();
    await flushPromises();
    expect(w.find("button.btn-ghost").exists()).toBe(false);
  });
});
