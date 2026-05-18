<script setup lang="ts">
/**
 * FpEditor — 功能点编辑视图（v2.0 接入 AI Plugin）。
 *
 * v1 已有：上传文档、手工添加 FP、模块树、历史版本快照（functionsApi.snapshots）。
 * v2.0 GAP-A 新增：
 *   - 上传后告知用户去 Claude Code 跑 `/cost` 命令让 AI 抽取 FP 草稿
 *   - 30s 轮询 FP 列表，发现新增立即刷新并提示用户审核（5 分钟上限自动停）
 *   - source="claude_draft" 的 FP 行用浅黄底色 + AI 徽标，与 allocator 橙色拉开层级
 *
 * 不在前端跑 AI 抽取（同步阻塞 + 超时风险），转 Plugin 模式：上传只落文档，
 * 实际抽取由 Claude Code 终端发起，前端轮询拿结果。
 */
import { onMounted, onBeforeUnmount, ref, computed } from "vue";
import { useRouter } from "vue-router";
import { functionsApi, type FunctionPoint, type FpSnapshotMeta } from "@/api/functions";
import { uploadsApi } from "@/api/uploads";
import { formatBeijing } from "@/lib/datetime";
import { useResultsStore } from "@/stores/results";
import ModuleTree from "@/components/ModuleTree.vue";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import EmptyState from "@/components/status/EmptyState.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";
import AiTaskPanel from "@/components/fp/AiTaskPanel.vue";
import FpFormModal from "@/components/fp/FpFormModal.vue";
import UploadListSection from "@/components/fp/UploadListSection.vue";

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
const aiModalOpen = ref(false);
const uploadSection = ref<{ reload: () => Promise<void> } | null>(null);

// GAP-A: AI Plugin polling state. 上传完成后引导用户发起 AI 提取；
// 同时每 30s 轮询一次 FP 列表，发现 claude_draft 行数增加就停止并提示审核。
const fpFormOpen = ref(false);
const editingFp = ref<FunctionPoint | null>(null);

// 上传成功后的引导文案 —— 优先引导用户用「AI 任务面板」一键发起提取。
const UPLOADED_HINT =
  "已上传。点右上角「🤖 AI 任务面板」即可发起 AI 提取任务，" +
  "或在 Claude Code 终端运行 /cost-estimation:cost；也可继续手动添加。";

const aiPollHint = ref<string>("");
const aiPolling = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;
let pollStopTimer: ReturnType<typeof setTimeout> | null = null;
const POLL_INTERVAL_MS = 30_000;
const POLL_MAX_MS = 5 * 60 * 1000; // 5 分钟自动停
const lastFpCount = ref(0);

const isEmpty = computed(() => !loading.value && error.value === null && functions.value.length === 0);
const isError = computed(() => !loading.value && error.value !== null);

// 模块树选中过滤 —— null = 全部
type ModuleSel = { subsystem: string; l1_module: string } | null;
const selectedModule = ref<ModuleSel>(null);

// 表格行 = 过滤后的 FP，但保留在完整列表里的原始序号（# 列稳定）
const displayedRows = computed(() => {
  const rows = functions.value.map((fp, i) => ({ fp, num: i + 1 }));
  const sel = selectedModule.value;
  if (!sel) return rows;
  return rows.filter(
    (r) =>
      (r.fp.subsystem ?? "未分组") === sel.subsystem &&
      (r.fp.l1_module ?? "未分类") === sel.l1_module,
  );
});

function onModuleSelect(payload: ModuleSel): void {
  selectedModule.value = payload;
}

onMounted(async () => {
  await load();
});

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
    // GAP-A: AI 提取可在「AI 任务面板」一键发起，也可走 Claude Code 终端。
    // 同时开启 polling，等 AI 写入；并刷新主页面的已上传文件区块。
    window.alert(UPLOADED_HINT);
    aiPollHint.value = UPLOADED_HINT;
    await uploadSection.value?.reload();
    startAiPolling();
  } catch (err: unknown) {
    // 上传失败用弹窗提示真实原因（如「文件超过 100MB」），不要塞进
    // 「功能点加载失败」那个 banner —— 那是 FP 列表加载错误专用的。
    const msg = err instanceof Error ? err.message : "上传失败";
    window.alert("文件上传失败：" + msg);
  } finally {
    uploading.value = false;
    input.value = "";
  }
}

// pollTimer 守卫确保重复点上传不会启动多个 interval；
// POLL_MAX_MS 上限避免用户离开页面后无限轮询消耗后端
function startAiPolling(): void {
  if (pollTimer) return;
  aiPolling.value = true;
  lastFpCount.value = functions.value.length;
  pollTimer = setInterval(() => {
    void pollOnce();
  }, POLL_INTERVAL_MS);
  pollStopTimer = setTimeout(() => {
    stopAiPolling();
    if (aiPollHint.value && !aiPollHint.value.includes("条 FP 草稿")) {
      aiPollHint.value = "已停止轮询。如已运行 /cost 但未看到草稿，请手动刷新页面。";
    }
  }, POLL_MAX_MS);
}

async function pollOnce(): Promise<void> {
  try {
    const resp = await functionsApi.list(props.projectId);
    functions.value = resp;
    const delta = functions.value.length - lastFpCount.value;
    if (delta > 0) {
      stopAiPolling();
      aiPollHint.value = `AI 写入了 ${delta} 条 FP 草稿，请审核。`;
    }
  } catch {
    // 轮询失败不打断用户，下次再试；超过 POLL_MAX_MS 会自动停。
  }
}

function stopAiPolling(): void {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  if (pollStopTimer) {
    clearTimeout(pollStopTimer);
    pollStopTimer = null;
  }
  aiPolling.value = false;
}

onBeforeUnmount(stopAiPolling);

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
  return formatBeijing(iso);
}

function sourceLabel(source: FunctionPoint["source"] | undefined): string {
  if (source === "allocator") return "预算倒推";
  if (source === "ai_extracted") return "AI 提取";
  if (source === "claude_draft") return "AI 草稿";
  return "手工";
}

function sourceBadgeClass(source: FunctionPoint["source"] | undefined): string {
  if (source === "allocator") return "badge badge-warning";
  if (source === "ai_extracted") return "badge badge-data";
  if (source === "claude_draft") return "badge badge-ai";
  return "badge badge-muted";
}

async function reloadFps(): Promise<void> {
  await load();
}

function openCreateFp(): void {
  editingFp.value = null;
  fpFormOpen.value = true;
}

function openEditFp(fp: FunctionPoint): void {
  editingFp.value = fp;
  fpFormOpen.value = true;
}

async function onDeleteFp(fp: FunctionPoint): Promise<void> {
  if (!window.confirm(`确定删除功能点「${fp.name || fp.id}」？`)) return;
  try {
    await functionsApi.remove(props.projectId, fp.id);
    await load();
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "删除失败";
  }
}

async function onFpSaved(): Promise<void> {
  await load();
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
          @click="openCreateFp"
        >
          + 添加功能点
        </button>
        <button
          type="button"
          class="btn"
          @click="goParams"
        >
          参数管理
        </button>
        <button
          type="button"
          class="btn"
          @click="router.push(`/projects/${projectId}/edit`)"
        >
          ⚙️ 编辑设定
        </button>
        <button
          type="button"
          class="btn"
          @click="aiModalOpen = true"
        >
          🤖 AI 任务面板
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

    <UploadListSection
      ref="uploadSection"
      :project-id="projectId"
    />

    <p
      v-if="aiPollHint && (isEmpty || isError)"
      class="ai-poll-hint"
      role="status"
    >
      <span>{{ aiPollHint }}</span>
      <button
        type="button"
        class="btn-link"
        @click="aiModalOpen = true"
      >
        打开 AI 任务面板
      </button>
      <button
        v-if="aiPolling"
        type="button"
        class="btn-link"
        @click="reloadFps"
      >
        立即刷新
      </button>
    </p>

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
        <ModuleTree
          :functions="functions"
          @select="onModuleSelect"
        />
      </aside>
      <main class="grid-body">
        <p
          v-if="aiPollHint"
          class="ai-poll-hint"
          role="status"
        >
          <span>{{ aiPollHint }}</span>
          <button
            type="button"
            class="btn-link"
            @click="aiModalOpen = true"
          >
            打开 AI 任务面板
          </button>
          <button
            v-if="aiPolling"
            type="button"
            class="btn-link"
            @click="reloadFps"
          >
            立即刷新
          </button>
        </p>
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">
                #
              </th>
              <th scope="col">
                功能点
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
                规模
              </th>
              <th scope="col">
                来源
              </th>
              <th scope="col">
                操作
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in displayedRows"
              :key="row.fp.id"
              :data-source="row.fp.source"
              :class="{
                'row-allocator': row.fp.source === 'allocator',
                'ai-draft': row.fp.source === 'claude_draft',
              }"
            >
              <td>{{ row.num }}</td>
              <td class="fp-name">
                <span class="fp-name-text">{{ row.fp.name || "—" }}</span>
                <span
                  v-if="row.fp.description"
                  class="fp-desc"
                  :title="row.fp.description"
                >{{ row.fp.description }}</span>
              </td>
              <td>{{ row.fp.subsystem || "—" }}</td>
              <td>{{ row.fp.l1_module || "—" }}</td>
              <td>{{ row.fp.category }}</td>
              <td>{{ row.fp.ufp }}</td>
              <td>{{ row.fp.us.toFixed(2) }}</td>
              <td>
                <span :class="sourceBadgeClass(row.fp.source)">{{ sourceLabel(row.fp.source) }}</span>
              </td>
              <td class="fp-ops">
                <button type="button" class="btn btn-sm" @click="openEditFp(row.fp)">编辑</button>
                <button type="button" class="btn btn-sm fp-del-btn" @click="onDeleteFp(row.fp)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p
          v-if="displayedRows.length === 0"
          class="muted filter-empty"
        >
          该模块下暂无功能点。
        </p>
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

    <AiTaskPanel
      v-model:open="aiModalOpen"
      :project-id="projectId"
    />

    <FpFormModal
      v-model:open="fpFormOpen"
      :project-id="projectId"
      :editing="editingFp"
      @saved="onFpSaved"
    />
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
.fp-name {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-width: 360px;
}
.fp-name-text {
  font-weight: 600;
}
.fp-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.filter-empty {
  padding: var(--space-4);
  text-align: center;
}
.row-allocator {
  background: var(--color-warning-bg);
}
.row-allocator:hover {
  background: var(--color-warning-bg) !important;
  filter: brightness(0.98);
}
/* GAP-A: claude_draft 行用浅黄底色 + AI 徽标，与 allocator 的橙色背景拉开层次。 */
.ai-draft {
  background: oklch(96% 0.06 95);
}
.ai-draft:hover {
  background: oklch(96% 0.06 95) !important;
  filter: brightness(0.98);
}
:deep(.badge-ai) {
  background: var(--color-warning, #ea580c);
  color: white;
}
.ai-poll-hint {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: rgba(22, 101, 255, 0.06);
  border: 1px solid rgba(22, 101, 255, 0.18);
  border-radius: var(--radius-md);
  margin: 0 0 var(--space-2) 0;
  font-size: var(--font-size-sm);
  color: var(--color-text);
}
.btn-link {
  background: none;
  border: none;
  color: var(--color-primary, #165dff);
  padding: 0;
  font-size: inherit;
  cursor: pointer;
  text-decoration: underline;
}
.btn-link:hover {
  filter: brightness(0.9);
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
.fp-ops {
  display: flex;
  gap: 6px;
}
.fp-del-btn {
  color: var(--red, #dc2626);
}
</style>
