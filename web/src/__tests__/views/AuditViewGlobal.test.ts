import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import AuditView from "@/views/AuditView.vue";

vi.mock("@/api/audit", () => ({
  auditApi: {
    list: vi.fn().mockResolvedValue([]),
    listGlobal: vi.fn(),
  },
}));
import { auditApi } from "@/api/audit";

const makeRouter = () =>
  createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/", component: { template: "<div/>" } }],
  });

const entry = (id: number, projectName: string) => ({
  id,
  project_id: `p-${id}`,
  project_name: projectName,
  ts: "2026-05-18T10:00:00Z",
  actor: "user",
  action: "project.update",
  target: null,
  diff_json: null,
});

const mountGlobal = async () => {
  const router = makeRouter();
  await router.push("/");
  return mount(AuditView, {
    props: { global: true },
    global: { plugins: [router] },
  });
};

describe("AuditView global 分支 (v2.7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("global=true 时调 auditApi.listGlobal 而非 list", async () => {
    (auditApi.listGlobal as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    await mountGlobal();
    await flushPromises();
    expect(auditApi.listGlobal).toHaveBeenCalled();
    expect(auditApi.list).not.toHaveBeenCalled();
  });

  it("渲染跨项目时间线并显示项目名徽章", async () => {
    (auditApi.listGlobal as ReturnType<typeof vi.fn>).mockResolvedValue([
      entry(2, "项目乙"),
      entry(1, "项目甲"),
    ]);
    const w = await mountGlobal();
    await flushPromises();
    expect(w.text()).toContain("项目甲");
    expect(w.text()).toContain("项目乙");
    expect(w.text()).not.toContain("将在 v2.3 上线");
  });

  it("满页时显示加载更多，点击后以最后一条 id 作游标续拉", async () => {
    const firstPage = Array.from({ length: 50 }, (_, i) => entry(100 - i, "P"));
    (auditApi.listGlobal as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce([entry(50, "P")]);
    const w = await mountGlobal();
    await flushPromises();
    const moreBtn = w.findAll("button").find((b) => b.text().includes("加载更多"));
    expect(moreBtn).toBeTruthy();
    await moreBtn!.trigger("click");
    await flushPromises();
    expect(auditApi.listGlobal).toHaveBeenLastCalledWith({ limit: 50, beforeId: 51 });
  });
});
