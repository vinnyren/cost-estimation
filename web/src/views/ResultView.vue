<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";
import { projectsApi, type Project } from "@/api/projects";
import { calcApi, type ForwardResult, type ReverseResult } from "@/api/calc";
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
const downloading = ref(false);

const targetTotal = ref(0);
const otherCost = ref(0);

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
  try {
    await reportsApi.download(props.projectId, `${project.value?.name ?? "report"}.xlsx`);
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "下载失败";
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
  justify-content: center;
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}
</style>
