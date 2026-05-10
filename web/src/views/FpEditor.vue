<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";
import { functionsApi, type FunctionPoint, type FpSnapshotMeta } from "@/api/functions";
import { uploadsApi } from "@/api/uploads";
import { useResultsStore } from "@/stores/results";
import ModuleTree from "@/components/ModuleTree.vue";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import EmptyState from "@/components/status/EmptyState.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";

const props = defineProps<{ projectId: string }>();

const router = useRouter();
// results store reserved for future use (stale tracking when params change)
useResultsStore();

const functions = ref<FunctionPoint[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const uploading = ref(false);
const historyOpen = ref(false);
const snapshots = ref<FpSnapshotMeta[]>([]);
const restoring = ref<number | null>(null);

const isEmpty = computed(() => !loading.value && error.value === null && functions.value.length === 0);
const isError = computed(() => !loading.value && error.value !== null);

onMounted(load);

async function load(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    const resp = await functionsApi.list(props.projectId);
    functions.value = resp;
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "加载失败";
  } finally {
    loading.value = false;
  }
}

function pickFile(): void {
  fileInput.value?.click();
}

async function onFileChange(e: Event): Promise<void> {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  uploading.value = true;
  try {
    await uploadsApi.upload(props.projectId, file);
    window.alert("上传完成。AI 提取功能将在 Phase 5 接入；请先手动添加功能点。");
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : "上传失败";
  } finally {
    uploading.value = false;
    input.value = "";
  }
}

async function calcAndGo(): Promise<void> {
  router.push({ name: "result-view", params: { id: props.projectId } });
}

function goParams(): void {
  router.push({ name: "param-manager", params: { id: props.projectId } });
}

async function toggleHistory(): Promise<void> {
  if (historyOpen.value) {
    historyOpen.value = false;
    return;
  }
  try {
    snapshots.value = await functionsApi.snapshots(props.projectId);
    historyOpen.value = true;
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "历史版本加载失败";
  }
}

async function restoreVersion(version: number): Promise<void> {
  const ok = window.confirm(
    `确定恢复到 version ${version}？当前的功能点会被替换为该版本快照（恢复前会自动留一份当前快照便于反悔）。`,
  );
  if (!ok) return;
  restoring.value = version;
  try {
    await functionsApi.restore(props.projectId, version);
    historyOpen.value = false;
    await load(); // 重新拉 FP 列表
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "恢复失败";
  } finally {
    restoring.value = null;
  }
}

function formatSnapTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("zh-CN");
  } catch {
    return iso;
  }
}

function sourceLabel(source: FunctionPoint["source"] | undefined): string {
  if (source === "allocator") return "预算倒推";
  if (source === "ai_extracted") return "AI 提取";
  return "手工";
}

function sourceBadgeClass(source: FunctionPoint["source"] | undefined): string {
  if (source === "allocator") return "badge badge-warning";
  if (source === "ai_extracted") return "badge badge-data";
  return "badge badge-muted";
}
</script>

<template>
  <section
    class="page"
    aria-labelledby="title"
  >
    <header class="page-header">
      <h1 id="title">
        FP 编辑（项目 #{{ projectId }}）
      </h1>
      <div class="actions">
        <div class="history-wrap">
          <button
            type="button"
            class="btn"
            :aria-expanded="historyOpen"
            @click="toggleHistory"
          >
            历史版本 {{ historyOpen ? "▴" : "▾" }}
          </button>
          <div
            v-if="historyOpen"
            class="history-pop"
            role="dialog"
            aria-label="功能点历史版本"
          >
            <p
              v-if="snapshots.length === 0"
              class="history-empty"
            >
              暂无快照（每次批量写入会自动留一版）。
            </p>
            <ol
              v-else
              class="history-list"
            >
              <li
                v-for="s in snapshots"
                :key="s.id"
              >
                <div class="history-meta">
                  <strong>v{{ s.version }}</strong>
                  <span class="text-muted">{{ formatSnapTime(s.snapshot_at) }}</span>
                  <span class="text-muted">{{ s.fp_count }} FP</span>
                  <span
                    v-if="s.reason"
                    class="text-muted"
                  >· {{ s.reason }}</span>
                </div>
                <button
                  type="button"
                  class="btn btn-sm"
                  :disabled="restoring !== null"
                  @click="restoreVersion(s.version)"
                >
                  {{ restoring === s.version ? "恢复中…" : "恢复此版本" }}
                </button>
              </li>
            </ol>
          </div>
        </div>
        <button
          type="button"
          class="btn"
          @click="goParams"
        >
          参数管理
        </button>
        <button
          type="button"
          class="btn btn-primary"
          @click="calcAndGo"
        >
          计算 → 结果页
        </button>
      </div>
    </header>

    <LoadingSkeleton
      v-if="loading"
      :rows="8"
    />

    <ErrorBanner
      v-else-if="isError"
      :problem="'功能点加载失败'"
      :cause="error ?? ''"
      :suggestion="'请刷新后重试'"
      :retryable="true"
      @retry="load"
    />

    <EmptyState
      v-else-if="isEmpty"
      :title="'还没有功能点'"
      :description="'上传文档让 AI 写第一稿，或手动添加'"
      :cta-label="uploading ? '上传中…' : '上传文档让 AI 写第一稿'"
      @cta-click="pickFile"
    />

    <div
      v-else
      class="layout"
    >
      <aside class="sidebar">
        <ModuleTree :functions="functions" />
      </aside>
      <main class="grid-body">
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">
                #
              </th>
              <th scope="col">
                子系统
              </th>
              <th scope="col">
                一级模块
              </th>
              <th scope="col">
                类别
              </th>
              <th scope="col">
                UFP
              </th>
              <th scope="col">
                US
              </th>
              <th scope="col">
                来源
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(fp, i) in functions"
              :key="fp.id"
              :data-source="fp.source"
              :class="{ 'row-allocator': fp.source === 'allocator' }"
            >
              <td>{{ i + 1 }}</td>
              <td>{{ fp.subsystem }}</td>
              <td>{{ fp.l1_module }}</td>
              <td>{{ fp.category }}</td>
              <td>{{ fp.ufp }}</td>
              <td>{{ fp.us.toFixed(2) }}</td>
              <td>
                <span :class="sourceBadgeClass(fp.source)">{{ sourceLabel(fp.source) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </main>
    </div>

    <input
      ref="fileInput"
      type="file"
      accept=".pdf,.docx,.xlsx,.md,.txt"
      aria-label="上传需求文档（PDF/Word/Excel/MD/TXT）"
      hidden
      @change="onFileChange"
    >
  </section>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  height: calc(100vh - var(--layout-header-height) - var(--space-6) * 2);
  min-height: 480px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
  flex-shrink: 0;
}
.page-header h1 {
  margin: 0;
}
.actions {
  display: flex;
  gap: var(--space-2);
}
.layout {
  display: flex;
  flex: 1;
  min-height: 0;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}
.sidebar {
  border-right: 1px solid var(--color-border);
  background: var(--color-bg-hover);
  flex-shrink: 0;
}
.grid-body {
  flex: 1;
  min-width: 0;
  overflow: auto;
  padding: var(--space-3);
}
/* 窄屏：240px sidebar 把表格挤到只剩一两列。改为竖排 + 表格水平滚动。
   断点选 768px 与全局 .cards 一致。 */
@media (max-width: 768px) {
  .layout {
    flex-direction: column;
  }
  .sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
    max-height: 30vh;
    overflow: auto;
  }
}
.grid-body table.data-table {
  border: none;
  box-shadow: none;
}
.row-allocator {
  background: var(--color-warning-bg);
}
.row-allocator:hover {
  background: var(--color-warning-bg) !important;
  filter: brightness(0.98);
}
.history-wrap {
  position: relative;
}
.history-pop {
  position: absolute;
  top: calc(100% + var(--space-1));
  right: 0;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: var(--space-3);
  min-width: 320px;
  max-width: 480px;
  max-height: 60vh;
  overflow: auto;
  z-index: 10;
}
.history-empty {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}
.history-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.history-list li {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--color-bg-hover);
}
.history-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: var(--font-size-sm);
}
.btn-sm {
  padding: 4px 10px;
  font-size: var(--font-size-sm);
}
</style>
