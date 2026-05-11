import { ref, onUnmounted } from "vue";
import { aiTasksApi, type AiTask } from "@/api/aiTasks";

const POLL_INTERVAL_MS = 1500;

export function useAiTaskPolling(projectId: string) {
  const task = ref<AiTask | null>(null);
  const polling = ref(false);
  let timer: ReturnType<typeof setInterval> | null = null;

  async function fetchLatest() {
    try {
      const tasks = await aiTasksApi.list(projectId);
      task.value = tasks[0] ?? null;
    } catch {
      // swallow — modal 不阻断
    }
  }

  function stop() {
    polling.value = false;
    if (timer) clearInterval(timer);
    timer = null;
  }

  function start() {
    if (polling.value) return;
    polling.value = true;
    void fetchLatest();
    timer = setInterval(() => {
      void fetchLatest();
      if (task.value && (task.value.status === "done" || task.value.status === "failed")) {
        stop();
      }
    }, POLL_INTERVAL_MS);
  }

  onUnmounted(stop);
  return { task, polling, start, stop, fetchLatest };
}
