<script setup lang="ts">
/**
 * UploadListSection — FpEditor 主页面内联展示「已上传文件」。
 *
 * 取代原 toolbar 按钮 + UploadListModal 弹窗：上传文件作为项目上下文
 * 常驻主页面，无需点按钮才能看。0 个文件时整块不渲染（EmptyState 已引导上传）。
 */
import { ref, onMounted } from "vue";
import { uploadsApi, type UploadRecord } from "@/api/uploads";

const props = defineProps<{ projectId: string }>();
const emit = defineEmits<{ refreshed: [count: number] }>();

const items = ref<UploadRecord[]>([]);
const loading = ref(true);
const hint = ref("");

async function load() {
  loading.value = true;
  hint.value = "";
  try {
    items.value = await uploadsApi.list(props.projectId);
    emit("refreshed", items.value.length);
  } catch (e) {
    hint.value = e instanceof Error ? e.message : "加载失败";
  } finally {
    loading.value = false;
  }
}

async function onRemove(rec: UploadRecord) {
  if (!window.confirm(`确定删除「${rec.filename}」？删除后无法恢复。`)) return;
  try {
    await uploadsApi.remove(props.projectId, rec.id);
    await load();
  } catch (e) {
    hint.value = e instanceof Error ? e.message : "删除失败";
  }
}

function fmtSize(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function fmtTime(s: string): string {
  return s.replace("T", " ").slice(0, 16);
}

defineExpose({ reload: load });

onMounted(load);
</script>

<template>
  <section
    v-if="!loading && items.length > 0"
    class="upload-section"
    aria-label="已上传文件"
  >
    <div class="upload-head">
      <h2 class="upload-title">
        📁 已上传文件
        <span class="upload-count">{{ items.length }}</span>
      </h2>
    </div>
    <table class="upload-table">
      <thead>
        <tr>
          <th scope="col">文件名</th>
          <th scope="col" class="col-size">大小</th>
          <th scope="col" class="col-type">类型</th>
          <th scope="col" class="col-time">上传时间</th>
          <th scope="col" class="col-op">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="r in items"
          :key="r.id"
          :data-upload-id="r.id"
        >
          <td class="cell-name">{{ r.filename }}</td>
          <td class="mono">{{ fmtSize(r.size) }}</td>
          <td><span class="badge">{{ r.filetype }}</span></td>
          <td class="mono cell-time">{{ fmtTime(r.uploaded_at) }}</td>
          <td>
            <button
              type="button"
              class="btn btn-sm btn-ghost btn-danger"
              @click="onRemove(r)"
            >
              删除
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <p
      v-if="hint"
      class="upload-hint"
      role="status"
    >
      {{ hint }}
    </p>
  </section>
</template>

<style scoped>
.upload-section {
  flex-shrink: 0;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-3);
}
.upload-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}
.upload-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  font-size: var(--font-size-base);
  font-weight: 600;
}
.upload-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 11px;
  background: var(--color-primary, #165dff);
  color: #fff;
  font-size: var(--font-size-sm);
  font-weight: 600;
}
.upload-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}
.upload-table thead th {
  text-align: left;
  padding: var(--space-2);
  color: var(--color-text-muted);
  font-weight: 500;
  border-bottom: 1px solid var(--color-border);
}
.upload-table tbody td {
  padding: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}
.upload-table tbody tr:last-child td {
  border-bottom: none;
}
.upload-table tbody tr:hover {
  background: var(--color-bg-hover);
}
.cell-name {
  font-weight: 600;
}
.cell-time {
  font-size: 11px;
  color: var(--color-text-muted);
}
.col-size { width: 100px; }
.col-type { width: 80px; }
.col-time { width: 140px; }
.col-op { width: 72px; }
.mono {
  font-family: var(--font-mono, monospace);
}
.btn-danger {
  color: var(--color-danger, var(--red, #dc2626));
}
.upload-hint {
  margin: var(--space-2) 0 0;
  padding: var(--space-2) var(--space-3);
  background: var(--color-warning-bg, #fef3c7);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
}
</style>
