<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";
import { functionsApi, type FunctionPoint } from "@/api/functions";
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
</style>
