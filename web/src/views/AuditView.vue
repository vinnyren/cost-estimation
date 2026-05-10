<script setup lang="ts">
// v2.0 T21 — Per-project audit timeline (GAP-J 前端).
//
// Reads /api/projects/:id/audit (paginated by id desc, see auditApi.list).
// The action codes are stable strings emitted by the server; we translate
// them to human labels via ACTION_LABELS. Unknown codes fall back to the
// raw code so a new server event never produces a blank row.
//
// Pagination is keyset-style ("beforeId" = id of the oldest row shown);
// "Load more" appends rather than replacing so the visible scrollback grows.
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import { auditApi, type AuditEntry } from "@/api/audit";

const PAGE_SIZE = 50;

const route = useRoute();
const projectId = route.params.id as string;
const entries = ref<AuditEntry[]>([]);
const loading = ref(false);

const ACTION_LABELS: Record<string, string> = {
  "project.create": "✨ 创建项目",
  "project.update": "✏️ 修改项目",
  "project.delete": "🗑️ 删除项目",
  "project.copy": "📋 复制项目",
  "fp.create": "➕ 添加 FP",
  "fp.update": "✏️ 修改 FP",
  "fp.delete": "➖ 删除 FP",
  "fp.bulk_write": "📦 批量写入 FP",
  "fp.restore": "🔄 恢复 FP 快照",
  "params.override": "⚙️ 修改参数",
  "upload.create": "📁 上传文档",
  "upload.delete": "🗑️ 删除上传",
  "calc.run": "🧮 执行计算",
  "report.export": "📤 导出报告",
};

async function reload(beforeId?: number): Promise<void> {
  loading.value = true;
  try {
    const more = await auditApi.list(projectId, { limit: PAGE_SIZE, beforeId });
    if (beforeId !== undefined) {
      entries.value = [...entries.value, ...more];
    } else {
      entries.value = more;
    }
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void reload();
});

async function onLoadMore(): Promise<void> {
  const last = entries.value[entries.value.length - 1];
  if (last) await reload(last.id);
}

function formatTs(ts: string): string {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString();
}

function labelFor(action: string): string {
  return ACTION_LABELS[action] ?? action;
}
</script>

<template>
  <section
    class="audit-view"
    aria-labelledby="audit-title"
  >
    <header class="page-header">
      <router-link
        :to="`/projects/${projectId}/functions`"
        class="back"
      >
        ← 返回项目
      </router-link>
      <h2 id="audit-title">
        审计日志
      </h2>
    </header>
    <ol class="timeline">
      <li
        v-for="e in entries"
        :key="e.id"
        class="audit-row"
        data-testid="audit-row"
      >
        <time>{{ formatTs(e.ts) }}</time>
        <strong>{{ labelFor(e.action) }}</strong>
        <span
          v-if="e.target && e.target !== projectId"
          class="target"
        >→ {{ e.target }}</span>
        <span
          v-if="e.actor"
          class="actor"
        >· {{ e.actor }}</span>
      </li>
      <li
        v-if="entries.length === 0 && !loading"
        class="empty"
        data-testid="audit-empty"
      >
        暂无审计记录
      </li>
      <li
        v-if="entries.length === 0 && loading"
        class="empty"
        data-testid="audit-loading"
      >
        加载中…
      </li>
    </ol>
    <button
      v-if="entries.length >= PAGE_SIZE"
      type="button"
      class="btn btn-secondary"
      :disabled="loading"
      data-testid="audit-load-more"
      @click="onLoadMore"
    >
      {{ loading ? "加载中…" : "加载更早记录" }}
    </button>
  </section>
</template>

<style scoped>
.audit-view {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.page-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.page-header h2 {
  margin: 0;
  color: var(--color-text-title);
}
.back {
  color: var(--color-text-muted);
  text-decoration: none;
  font-size: var(--font-size-sm);
}
.back:hover {
  color: var(--color-primary);
}
.timeline {
  list-style: none;
  padding: 0;
  margin: 0;
  background: var(--color-bg-elevated, #fff);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}
.audit-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  font-size: var(--font-size-sm);
}
.audit-row:last-child {
  border-bottom: none;
}
.audit-row time {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  min-width: 160px;
  font-variant-numeric: tabular-nums;
}
.audit-row strong {
  color: var(--color-text-title);
  font-weight: 500;
}
.audit-row .target,
.audit-row .actor {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}
.empty {
  padding: var(--space-6);
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}
.btn-secondary {
  align-self: center;
  padding: var(--space-2) var(--space-4);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-body);
  cursor: pointer;
}
.btn-secondary:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
