import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import AiTaskPanel from "@/components/fp/AiTaskPanel.vue";

vi.mock("@/api/aiTasks", () => ({
  aiTasksApi: {
    list: vi.fn(),
    create: vi.fn(),
    start: vi.fn(),
    stop: vi.fn(),
  },
}));
import { aiTasksApi } from "@/api/aiTasks";

const mockTask = (overrides: Partial<{ id: string; status: string; progress_pct: number }> = {}) => ({
  id: "task-abcdef12-3456",
  project_id: "p-1",
  kind: "extract",
  status: "running",
  progress_pct: 50,
  stage_log: "✓ 解析\n✓ 切分",
  output_json: null,
  error_message: null,
  created_at: "2026-05-12T10:00:00Z",
  updated_at: "2026-05-12T10:00:30Z",
  ...overrides,
});

describe("AiTaskPanel (v2.5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty state when no tasks", async () => {
    (aiTasksApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    const w = mount(AiTaskPanel, { props: { open: true, projectId: "p-1" } });
    await flushPromises();
    expect(w.text()).toContain("暂无任务");
  });

  it("renders task rows + progress bar", async () => {
    (aiTasksApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([mockTask({ status: "running", progress_pct: 30 })]);
    const w = mount(AiTaskPanel, { props: { open: true, projectId: "p-1" } });
    await flushPromises();
    expect(w.find(".task-row.status-running").exists()).toBe(true);
    expect(w.text()).toContain("30%");
  });

  it("createAndStart calls create then start then reloads", async () => {
    (aiTasksApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (aiTasksApi.create as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask({ status: "queued" }));
    (aiTasksApi.start as ReturnType<typeof vi.fn>).mockResolvedValue({ pid: 999 });
    const w = mount(AiTaskPanel, { props: { open: true, projectId: "p-1" } });
    await flushPromises();
    const newBtn = w.findAll("button").find((b) => b.text().includes("新建"));
    await newBtn!.trigger("click");
    await flushPromises();
    expect(aiTasksApi.create).toHaveBeenCalledWith("p-1", "extract");
    expect(aiTasksApi.start).toHaveBeenCalledWith("task-abcdef12-3456");
  });
});
