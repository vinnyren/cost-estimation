<script setup lang="ts">
/**
 * ResultView — 计算结果页（v2.0 反向路径加 allocator panel）。
 *
 * 两个模式共用同一个 view：
 *   - 正向：onMounted 直接调 calcApi.forward 渲染 P10/P50/P90 三档总成本卡片
 *   - 反向：用户输入目标总造价 + 其他费用 → calcApi.reverse 给出三档 FP →
 *           （v2.0 GAP-C 新增）allocator panel 让用户输入模块草稿，调
 *           calcApi.allocate 把推荐档总 FP 按权重分摊到各模块
 *
 * 模块草稿支持锁定项 (locked_us)：先扣除锁定额度，剩余规模按 weight 分摊。
 * 用户也可在 Claude Code 跑 /cost-allocate 让 AI 生成 drafts 数组再贴回来。
 *
 * StaleBanner 监听 results.isStale — 参数页改了 override 后回到这里会提示重算。
 */
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";
import { projectsApi, type Project } from "@/api/projects";
import {
  calcApi,
  type ForwardResult,
  type ReverseResult,
  type AllocateOutput,
} from "@/api/calc";
import { reportsApi } from "@/api/reports";
import { useResultsStore } from "@/stores/results";
import ResultCard from "@/components/ResultCard.vue";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";
import StaleBanner from "@/components/status/StaleBanner.vue";

const props = defineProps<{ projectId: string }>();

const router = useRouter();
const results = useResultsStore();

const project = ref<Project | null>(null);
const forwardResult = ref<ForwardResult | null>(null);
const reverseResult = ref<ReverseResult | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
// download error is rendered separately so the banner doesn't claim
// "计算失败" when the download path is the actual failure
const downloadError = ref<string | null>(null);
const downloading = ref(false);

const targetTotal = ref(0);
const otherCost = ref(0);

// GAP-C: 反向 allocator — 把反向结果 P50 总规模按模块草稿权重分摊。
const allocating = ref(false);
const allocateHint = ref<string>("");
const allocResult = ref<AllocateOutput[]>([]);
const DEFAULT_DRAFTS_JSON = JSON.stringify(
  [
    { name: "前端", weight: 1 },
    { name: "后端", weight: 1.5 },
  ],
  null,
  0,
);

// 用反向计算的推荐档（默认 P50）作为分摊基数，与计算页其它地方的 band 语义保持一致
async function onAllocate(): Promise<void> {
  if (!reverseResult.value) {
    allocateHint.value = "请先点击「反算」生成三档 FP 结果。";
    return;
  }
  const band = reverseResult.value.recommended_band ?? "P50";
  const targetUs = reverseResult.value.scale_adjusted_bands?.[band];
  if (!targetUs || targetUs <= 0) {
    allocateHint.value = "无可用推荐档 FP — 请确认反向结果完整。";
    return;
  }
  const draftsInput = window.prompt(
    '输入模块草稿（JSON 数组，如 [{"name":"前端","weight":1},{"name":"后端","weight":1.5}]）。\n或在 Claude Code 跑 /cost-allocate <project_id> 让 AI 生成。',
    DEFAULT_DRAFTS_JSON,
  );
  if (!draftsInput) return;
  let drafts: Array<{ name: string; weight: number; locked?: boolean; locked_us?: number }>;
  try {
    drafts = JSON.parse(draftsInput);
    if (!Array.isArray(drafts) || drafts.length === 0) {
      throw new Error("drafts must be a non-empty array");
    }
  } catch (e: unknown) {
    allocateHint.value =
      "输入不是合法 JSON 数组：" + (e instanceof Error ? e.message : String(e));
    return;
  }
  allocating.value = true;
  allocateHint.value = "";
  try {
    allocResult.value = await calcApi.allocate({
      project_id: props.projectId,
      target_us: targetUs,
      cf: reverseResult.value.cf_used,
      drafts,
    });
  } catch (e: unknown) {
    allocateHint.value = e instanceof Error ? e.message : "分摊失败";
  } finally {
    allocating.value = false;
  }
}

onMounted(loadAndCompute);

async function loadAndCompute(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    project.value = await projectsApi.get(props.projectId);
    if (project.value.mode === "forward") {
      const r = await calcApi.forward({ project_id: props.projectId });
      forwardResult.value = r;
      results.setForwardResult(r);
    } else {
      // reverse 模式：从向导/编辑保存的 target_cost 预填，省一次手输
      targetTotal.value = project.value.target_cost ?? 0;
      otherCost.value = project.value.other_cost ?? 0;
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "计算失败";
  } finally {
    loading.value = false;
  }
}

async function reverseCalc(): Promise<void> {
  if (!project.value) return;
  if (targetTotal.value <= 0) {
    error.value = "请输入目标金额";
    return;
  }
  loading.value = true;
  try {
    const r = await calcApi.reverse({
      project_id: props.projectId,
      target_total: targetTotal.value,
      other_cost: otherCost.value,
    });
    reverseResult.value = r;
    results.setReverseResult(r);
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "反算失败";
  } finally {
    loading.value = false;
  }
}

async function download(): Promise<void> {
  downloading.value = true;
  downloadError.value = null;
  try {
    await reportsApi.download(props.projectId, `${project.value?.name ?? "report"}.xlsx`);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "下载失败";
    // 反向项目无 FP 时后端会回 FP_EMPTY/400 — 给个能行动的提示
    if (project.value?.mode === "reverse" && /FP_EMPTY|status code 400/i.test(msg)) {
      downloadError.value =
        "反向项目导出 Excel 需要先在 FP 编辑屏录入功能点（基于推荐档位的 FP 数量）";
    } else {
      downloadError.value = msg;
    }
  } finally {
    downloading.value = false;
  }
}

function back(): void {
  router.push({ name: "fp-editor", params: { id: props.projectId } });
}

const hasForward = computed(() => forwardResult.value !== null);
const hasReverse = computed(() => reverseResult.value !== null);
</script>

<template>
  <section
    class="page"
    aria-labelledby="title"
  >
    <header class="page-header">
      <h1 id="title">
        评估结果（项目 #{{ projectId }} ·
        {{ project?.mode === "reverse" ? "反向" : "正向" }}）
      </h1>
      <button
        type="button"
        class="btn"
        @click="back"
      >
        返回 FP 编辑
      </button>
    </header>

    <StaleBanner
      v-if="results.isStale"
      @recompute="loadAndCompute"
    />

    <LoadingSkeleton
      v-if="loading"
      :rows="3"
    />

    <ErrorBanner
      v-else-if="error"
      :problem="'计算失败'"
      :cause="error"
      :suggestion="'请检查参数与功能点后重试'"
      :retryable="true"
      @retry="loadAndCompute"
    />

    <div
      v-else-if="project?.mode === 'forward' && hasForward"
      class="cards"
    >
      <ResultCard
        :band="'P10'"
        :value="forwardResult!.cost_total_yuan.P10"
        :unit="'元'"
        :description="`${forwardResult!.effort_dev_hours.P10.toFixed(0)} 人时`"
      />
      <ResultCard
        :band="'P50'"
        :value="forwardResult!.cost_total_yuan.P50"
        :unit="'元'"
        :recommended="true"
        :description="`${forwardResult!.effort_dev_hours.P50.toFixed(0)} 人时 · 规模 ${forwardResult!.scale_adjusted.toFixed(2)} FP`"
      />
      <ResultCard
        :band="'P90'"
        :value="forwardResult!.cost_total_yuan.P90"
        :unit="'元'"
        :description="`${forwardResult!.effort_dev_hours.P90.toFixed(0)} 人时`"
      />
    </div>

    <div
      v-else-if="project?.mode === 'reverse'"
      class="reverse"
    >
      <fieldset class="card reverse-card">
        <legend>反算输入</legend>
        <label class="field">
          <span class="field-label">目标总造价（元）</span>
          <input
            v-model.number="targetTotal"
            type="number"
            min="0"
          >
        </label>
        <label class="field">
          <span class="field-label">其他费用（元）</span>
          <input
            v-model.number="otherCost"
            type="number"
            min="0"
          >
        </label>
        <div class="reverse-actions">
          <button
            type="button"
            class="btn btn-primary"
            @click="reverseCalc"
          >
            反算
          </button>
        </div>
      </fieldset>

      <div
        v-if="hasReverse"
        class="cards"
      >
        <ResultCard
          :band="'P10'"
          :value="reverseResult!.scale_adjusted_bands.P10"
          :unit="'FP'"
          :recommended="reverseResult!.recommended_band === 'P10'"
          :description="'乐观（高生产率假设 → FP 较大）'"
        />
        <ResultCard
          :band="'P50'"
          :value="reverseResult!.scale_adjusted_bands.P50"
          :unit="'FP'"
          :recommended="reverseResult!.recommended_band === 'P50'"
          :description="'中位（建议采纳）'"
        />
        <ResultCard
          :band="'P90'"
          :value="reverseResult!.scale_adjusted_bands.P90"
          :unit="'FP'"
          :recommended="reverseResult!.recommended_band === 'P90'"
          :description="'保守（低生产率假设 → FP 较小）'"
        />
      </div>

      <section
        v-if="hasReverse"
        class="allocator-panel"
        aria-labelledby="alloc-title"
      >
        <h3 id="alloc-title">
          AI 模块分摊（GAP-C）
        </h3>
        <p class="alloc-desc">
          反向计算给出三档总 FP；输入模块草稿（或让 Claude 通过 <code>/cost-allocate</code> 生成）→
          按权重把推荐档总规模分摊到各模块。
        </p>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="allocating"
          @click="onAllocate"
        >
          {{ allocating ? "计算中…" : "生成模块分摊" }}
        </button>
        <p
          v-if="allocateHint"
          class="hint"
          role="status"
        >
          {{ allocateHint }}
        </p>
        <table
          v-if="allocResult.length > 0"
          class="alloc-table"
          aria-label="模块分摊结果"
        >
          <thead>
            <tr>
              <th scope="col">
                模块
              </th>
              <th scope="col">
                分配 US（FP）
              </th>
              <th scope="col">
                锁定
              </th>
              <th scope="col">
                审计标签
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="r in allocResult"
              :key="r.name"
              data-testid="alloc-row"
            >
              <td>{{ r.name }}</td>
              <td>{{ r.us.toFixed(2) }}</td>
              <td>{{ r.locked ? "是" : "否" }}</td>
              <td>{{ r.audit_tag ?? "—" }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <footer
      v-if="hasForward || hasReverse"
      class="dl-bar"
    >
      <button
        type="button"
        class="btn btn-primary"
        :disabled="downloading"
        @click="download"
      >
        {{ downloading ? "下载中…" : "下载 Excel 报告" }}
      </button>
      <p
        v-if="downloadError"
        class="dl-error"
        role="alert"
      >
        下载失败：{{ downloadError }}
      </p>
    </footer>
  </section>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.page-header h1 {
  margin: 0;
}
.cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
  align-items: stretch;
}
@media (max-width: 768px) {
  .cards {
    grid-template-columns: 1fr;
  }
}
.reverse {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.reverse-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
}
.reverse-card legend {
  font-weight: 600;
  font-size: var(--font-size-md);
  color: var(--color-text-title);
  padding: 0 var(--space-2);
}
.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.field-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: 500;
}
.reverse-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-2);
}
.dl-bar {
  margin-top: var(--space-4);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}
.dl-error {
  margin: 0;
  color: var(--color-danger, #d4380d);
  font-size: var(--font-size-sm);
  text-align: center;
  max-width: 60ch;
}
.allocator-panel {
  margin-top: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.allocator-panel h3 {
  margin: 0;
  font-size: var(--font-size-md);
  color: var(--color-text-title);
}
.alloc-desc {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}
.alloc-desc code {
  background: var(--color-bg-muted, #f5f5f5);
  padding: 0 4px;
  border-radius: 3px;
  font-size: 0.95em;
}
.alloc-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: var(--space-2);
}
.alloc-table th,
.alloc-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border);
  text-align: left;
  font-size: var(--font-size-sm);
}
.alloc-table th {
  color: var(--color-text-muted);
  font-weight: 500;
}
.hint {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}
</style>
