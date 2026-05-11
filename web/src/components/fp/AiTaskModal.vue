<script setup lang="ts">
import { onMounted, onBeforeUnmount, watch } from "vue";
import { useAiTaskPolling } from "@/composables/useAiTaskPolling";

const props = defineProps<{ open: boolean; projectId: string }>();
const emit = defineEmits<{ "update:open": [v: boolean] }>();

const { task, start, stop } = useAiTaskPolling(props.projectId);

onMounted(() => {
  if (props.open) start();
});
onBeforeUnmount(stop);

// Restart polling when modal re-opens
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) start();
    else stop();
  },
);

function close() {
  stop();
  emit("update:open", false);
}
</script>

<template>
  <div v-if="open" class="modal-backdrop" @click="close">
    <div class="card ai-modal" @click.stop>
      <div class="ai-modal-head">
        <div class="ai-modal-spark">✨</div>
        <div class="ai-modal-meta">
          <div class="ai-modal-title">Claude AI 提取任务</div>
          <div class="muted" style="font-size: 12px">
            <template v-if="task">任务 ID {{ task.id.slice(0, 8) }}</template>
            <template v-else
              >暂无任务 — 在终端运行
              <span class="mono">/cost {{ projectId }}</span> 让 Claude 启动提取</template
            >
          </div>
        </div>
        <button class="btn btn-ghost btn-sm" @click="close">关闭</button>
      </div>

      <template v-if="task">
        <div class="ai-modal-log">
          <pre>{{ task.stage_log || "（等待 plugin 上报日志）" }}</pre>
        </div>
        <div v-if="task.status === 'failed' && task.error_message" class="banner banner-amber" style="margin-top: 12px">
          ⚠ 任务失败：{{ task.error_message }}
        </div>
        <div class="ai-modal-progress">
          <div class="ai-modal-bar">
            <div class="ai-modal-bar-fill" :style="{ width: task.progress_pct + '%' }" />
          </div>
          <div class="muted mono" style="font-size: 11px; margin-top: 4px">
            {{ task.progress_pct.toFixed(0) }}% · {{ task.status }}
          </div>
        </div>
      </template>

      <div class="ai-modal-foot">
        <button class="btn btn-ghost" @click="close">
          {{ task && task.status === "done" ? "查看结果" : task && task.status === "failed" ? "关闭" : "后台运行" }}
        </button>
        <button v-if="task && task.status === 'done'" class="btn btn-primary">采纳 FP</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: grid;
  place-items: center;
  z-index: 1000;
}
.ai-modal {
  width: 540px;
  padding: 24px;
}
.ai-modal-head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.ai-modal-spark {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  color: white;
  display: grid;
  place-items: center;
  font-size: 20px;
}
.ai-modal-meta {
  flex: 1;
}
.ai-modal-title {
  font-size: 16px;
  font-weight: 600;
}
.ai-modal-log {
  margin-top: 20px;
  padding: 14px;
  background: var(--surface-sunken);
  border-radius: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  max-height: 200px;
  overflow-y: auto;
}
.ai-modal-log pre {
  margin: 0;
  white-space: pre-wrap;
}
.ai-modal-progress {
  margin-top: 16px;
}
.ai-modal-bar {
  height: 6px;
  background: var(--surface-sunken);
  border-radius: 3px;
  overflow: hidden;
}
.ai-modal-bar-fill {
  height: 100%;
  transition: width 0.3s;
  background: linear-gradient(90deg, var(--accent), #7c3aed);
}
.ai-modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}
</style>
