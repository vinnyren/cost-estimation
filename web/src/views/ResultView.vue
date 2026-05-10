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
      // reverse 模式：等用户输入 target_total 后再算
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
    <header class="head">
      <h1 id="title">
        评估结果（项目 #{{ projectId }} ·
        {{ project?.mode === "reverse" ? "反向" : "正向" }}）
      </h1>
      <button
        type="button"
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
      <fieldset>
        <legend>反算输入</legend>
        <label>
          目标总造价（元）
          <input
            v-model.number="targetTotal"
            type="number"
            min="0"
          >
        </label>
        <label>
          其他费用（元）
          <input
            v-model.number="otherCost"
            type="number"
            min="0"
          >
        </label>
        <button
          type="button"
          @click="reverseCalc"
        >
          反算
        </button>
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

    <footer class="dl-bar">
      <button
        type="button"
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
  padding: var(--space-6);
  max-width: 1200px;
  margin: 0 auto;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}
.head button,
.reverse button,
.dl-bar button {
  min-height: 44px;
  padding: 0 var(--space-3);
}
.cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-4) 0;
}
.reverse fieldset {
  padding: var(--space-3);
  margin-bottom: var(--space-4);
  border: 1px solid oklch(85% 0 0);
  border-radius: var(--radius-md);
}
.reverse label {
  display: block;
  margin: var(--space-2) 0;
}
.reverse input {
  min-height: 44px;
  padding: 0 var(--space-2);
}
.dl-bar {
  margin-top: var(--space-6);
  display: flex;
  justify-content: center;
}
.dl-bar button {
  background: var(--color-accent);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  padding: 0 var(--space-6);
}
</style>
