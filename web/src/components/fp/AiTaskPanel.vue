<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from "vue";
import { aiTasksApi, type AiTask } from "@/api/aiTasks";
import { functionsApi } from "@/api/functions";
import { formatBeijing } from "@/lib/datetime";

const props = defineProps<{ open: boolean; projectId: string }>();
const emit = defineEmits<{
  "update:open": [v: boolean];
  accepted: [count: number];
}>();

const tasks = ref<AiTask[]>([]);
const loading = ref(false);
const hint = ref("");
let timer: ReturnType<typeof setInterval> | null = null;

async function load() {
  try {
    tasks.value = await aiTasksApi.list(props.projectId);
  } catch (e) {
    hint.value = e instanceof Error ? e.message : "加载失败";
  }
}

function stopPolling() {
  if (timer) { clearInterval(timer); timer = null; }
}

function startPolling() {
  stopPolling();
  load();
  timer = setInterval(() => {
    load();
  }, 1500);
}

async function onCreateAndStart() {
  loading.value = true;
  hint.value = "";
  try {
    const task = await aiTasksApi.create(props.projectId, "extract");
    await aiTasksApi.start(task.id);
    await load();
  } catch (e) {
    hint.value = e instanceof Error ? e.message : "创建任务失败";
  } finally {
    loading.value = false;
  }
}

async function onStop(task: AiTask) {
  if (!window.confirm(`确定停止任务 ${task.id.slice(0, 8)}？`)) return;
  try {
    await aiTasksApi.stop(task.id);
    await load();
  } catch (e) {
    hint.value = e instanceof Error ? e.message : "停止失败";
  }
}

const accepting = ref(false);

async function onAcceptDrafts() {
  accepting.value = true;
  hint.value = "";
  try {
    const result = await functionsApi.acceptDrafts(props.projectId);
    hint.value = `已采纳 ${result.accepted} 条功能点`;
    emit("accepted", result.accepted);
  } catch (e) {
    hint.value = e instanceof Error ? e.message : "采纳失败";
  } finally {
    accepting.value = false;
  }
}

watch(() => props.open, (v) => {
  if (v) startPolling(); else stopPolling();
});

onMounted(() => { if (props.open) startPolling(); });
onBeforeUnmount(stopPolling);

function close() { stopPolling(); emit("update:open", false); }
</script>

<template>
  <div v-if="open" class="modal-backdrop" @click="close">
    <div class="card task-panel" @click.stop>
      <div class="panel-head">
        <div>
          <div class="section-title">AI 任务面板</div>
          <div class="muted" style="font-size: 12px">项目 {{ projectId }} · 实时刷新</div>
        </div>
        <div style="display: flex; gap: 8px">
          <button class="btn btn-primary btn-sm" :disabled="loading" @click="onCreateAndStart">
            {{ loading ? "启动中…" : "+ 新建提取任务" }}
          </button>
          <button class="btn btn-ghost btn-sm" @click="close">关闭</button>
        </div>
      </div>

      <div v-if="hint" class="banner banner-amber" style="margin-top: 12px">{{ hint }}</div>

      <div v-if="tasks.length === 0" class="muted" style="padding: 32px; text-align: center">
        暂无任务 — 点 "+ 新建提取任务" 在后台运行 Claude 提取 FP
      </div>

      <div v-else class="task-list" style="margin-top: 12px; display: grid; gap: 10px">
        <div
          v-for="t in tasks"
          :key="t.id"
          class="task-row"
          :class="['status-' + t.status]"
          :data-task-id="t.id"
        >
          <div class="task-row-head">
            <span class="mono" style="font-size: 11px">{{ t.id.slice(0, 8) }}…</span>
            <span class="badge">{{ t.kind }}</span>
            <span
              class="badge"
              :class="t.status === 'done' ? 'badge-green' : t.status === 'failed' ? 'badge-amber' : t.status === 'running' ? 'badge-blue' : ''"
            >
              {{ t.status }}
            </span>
            <span class="muted mono" style="font-size: 10px">{{ formatBeijing(t.created_at) }}</span>
            <div style="flex: 1" />
            <button
              v-if="t.status === 'running'"
              class="btn btn-sm btn-ghost"
              style="color: var(--red)"
              @click="onStop(t)"
            >停止</button>
            <button
              v-else-if="t.status === 'done'"
              class="btn btn-sm btn-primary"
              :disabled="accepting"
              @click="onAcceptDrafts"
            >{{ accepting ? "采纳中…" : "采纳 FP" }}</button>
          </div>
          <div class="task-row-progress">
            <div class="bar"><div class="bar-fill" :style="{ width: t.progress_pct + '%' }" /></div>
            <span class="mono" style="font-size: 10px">{{ t.progress_pct.toFixed(0) }}%</span>
          </div>
          <pre v-if="t.stage_log" class="task-row-log">{{ t.stage_log }}</pre>
          <div v-if="t.error_message" class="banner banner-amber" style="font-size: 11px">⚠ {{ t.error_message }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: grid; place-items: center;
  z-index: 1000;
}
.task-panel { width: 720px; max-width: 92vw; max-height: 88vh; overflow-y: auto; padding: 24px; }
.panel-head { display: flex; align-items: flex-start; justify-content: space-between; }
.task-row {
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}
.task-row.status-running { border-left: 3px solid var(--accent); }
.task-row.status-done { border-left: 3px solid var(--green); }
.task-row.status-failed { border-left: 3px solid var(--amber); }
.task-row-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.task-row-progress { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.task-row-progress .bar { flex: 1; height: 5px; background: var(--surface-sunken); border-radius: 3px; overflow: hidden; }
.task-row-progress .bar-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--purple)); transition: width .3s; }
.task-row-log {
  margin: 0; padding: 8px 10px;
  background: var(--surface-sunken);
  border-radius: var(--radius);
  font-family: var(--font-mono);
  font-size: 10px; line-height: 1.4;
  max-height: 100px; overflow-y: auto;
  white-space: pre-wrap;
}
</style>
