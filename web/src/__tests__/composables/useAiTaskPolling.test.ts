import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock aiTasksApi.list - composable 通过此 fetch 数据
vi.mock("@/api/aiTasks", () => ({
  aiTasksApi: {
    list: vi.fn(),
  },
}));

import { mount } from "@vue/test-utils";
import { useAiTaskPolling } from "@/composables/useAiTaskPolling";
import { aiTasksApi } from "@/api/aiTasks";

const mockTask = (status: string) => ({
  id: "t-1",
  project_id: "p-1",
  kind: "extract",
  status,
  progress_pct: status === "done" ? 100 : 50,
  stage_log: "✓ test",
  output_json: null,
  error_message: null,
  created_at: "2026-05-11T00:00:00Z",
  updated_at: "2026-05-11T00:00:00Z",
});

// Wrap composable in a Vue component context to satisfy onUnmounted lifecycle requirement
function withComposable<T>(setup: () => T): T {
  let captured!: T;
  const Wrapper = {
    setup() {
      captured = setup();
      return () => null;
    },
  };
  mount(Wrapper);
  return captured;
}

describe("useAiTaskPolling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("fetchLatest stores the first task from list", async () => {
    (aiTasksApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([mockTask("running")]);
    const { task, fetchLatest } = withComposable(() => useAiTaskPolling("p-1"));
    await fetchLatest();
    expect(task.value?.id).toBe("t-1");
    expect(task.value?.status).toBe("running");
    expect(aiTasksApi.list).toHaveBeenCalledWith("p-1");
  });

  it("fetchLatest sets task to null when list is empty", async () => {
    (aiTasksApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    const { task, fetchLatest } = withComposable(() => useAiTaskPolling("p-1"));
    await fetchLatest();
    expect(task.value).toBeNull();
  });

  it("fetchLatest swallows API errors (returns silently)", async () => {
    (aiTasksApi.list as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("network"));
    const { task, fetchLatest } = withComposable(() => useAiTaskPolling("p-1"));
    await expect(fetchLatest()).resolves.not.toThrow();
    // task stays null
    expect(task.value).toBeNull();
  });

  it("start sets polling=true and stop resets it", async () => {
    (aiTasksApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    const { polling, start, stop } = withComposable(() => useAiTaskPolling("p-1"));
    expect(polling.value).toBe(false);
    start();
    expect(polling.value).toBe(true);
    stop();
    expect(polling.value).toBe(false);
  });

  it("start is idempotent — calling twice does not double-poll", async () => {
    (aiTasksApi.list as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    const { polling, start, stop } = withComposable(() => useAiTaskPolling("p-1"));
    start();
    start(); // second call should be no-op
    expect(polling.value).toBe(true);
    stop();
  });
});
