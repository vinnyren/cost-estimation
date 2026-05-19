<script setup lang="ts">
/**
 * ResultView — 计算结果页（v2.2 forward 用 ResultTrio + PipelineGrid + CostBar + ComplianceCard）。
 *
 * 两个模式共用同一个 view：
 *   - 正向：onMounted 直接调 calcApi.forward 渲染 ResultTrio（三档）+ PipelineGrid + CostBar + ComplianceCard
 *   - 反向：用户输入目标总造价 + 其他费用 → calcApi.reverse 给出三档 FP →
 *           allocator panel 让用户输入模块草稿，调
 *           calcApi.allocate 把推荐档总 FP 按权重分摊到各模块
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
  type AllocateResult,
} from "@/api/calc";
import { reportsApi } from "@/api/reports";
import { aiTasksApi } from "@/api/aiTasks";
import { useResultsStore } from "@/stores/results";
import ResultTrio from "@/components/result/ResultTrio.vue";
import PipelineGrid from "@/components/result/PipelineGrid.vue";
import CostBar from "@/components/result/CostBar.vue";
import ComplianceCard from "@/components/result/ComplianceCard.vue";
import ResultCard from "@/components/ResultCard.vue";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";
import StaleBanner from "@/components/status/StaleBanner.vue";
import AllocatorPanel from "@/components/result/AllocatorPanel.vue";

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

/** Currently selected cost band — persisted to project.selected_band */
const selectedBand = ref<"P10" | "P50" | "P90">("P50");

const targetTotal = ref(0);
const otherCost = ref(0);

const availableBudget = computed(() => {
  const avail = Math.max(0, targetTotal.value - otherCost.value);
  return avail.toLocaleString("zh-CN");
});

const REVERSE_BAND_LABEL: Record<string, string> = {
  P10: "乐观 · 最大可承载",
  P50: "中位 · 推荐采纳",
  P90: "保守 · 最少可保证",
};

const reverseTiers = computed(() => {
  if (!reverseResult.value) return [];
  const r = reverseResult.value;
  return (["P10", "P50", "P90"] as const).map((k) => ({
    key: k,
    label: REVERSE_BAND_LABEL[k],
    cost: 0,
    fp: r.scale_adjusted_bands[k],
    recommended: r.recommended_band === k,
    unit: "fp" as const,
    extras: [
      ["未调整规模", `${r.scale_unadjusted_bands[k].toFixed(2)} FP`],
    ] as Array<[string, string]>,
  }));
});

// allocResult stores the latest AllocateResult emitted by AllocatorPanel
const allocResult = ref<AllocateResult | null>(null);
// fpUpdatedMsg shows a brief confirmation when AllocatorPanel writes分摊结果回 FP 表
const fpUpdatedMsg = ref<string | null>(null);

function onAllocated(res: AllocateResult) {
  allocResult.value = res;
}

function onFpUpdated(count: number) {
  fpUpdatedMsg.value = `分摊结果已写回 ${count} 条功能点的规模。`;
}

onMounted(loadAndCompute);

async function loadAndCompute(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    project.value = await projectsApi.get(props.projectId);
    // Restore persisted band selection; fall back to P50
    selectedBand.value = project.value.selected_band ?? "P50";
    if (project.value.mode === "forward") {
      const r = await calcApi.forward({ project_id: props.projectId });
      forwardResult.value = r;
      results.setForwardResult(r);
    } else {
      // reverse 模式：从向导/编辑保存的 target_cost 预填，省一次手输
      targetTotal.value = project.value.target_cost ?? 0;
      otherCost.value = project.value.other_cost ?? 0;
      // 已有目标造价 → 进页面即自动反算，避免「第二次进入要再点一次反算」。
      if (targetTotal.value > 0) {
        await reverseCalc();
      }
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
    // 目标造价以万元录入，计算层以元运算 —— 调用反算 API 前换算。
    const r = await calcApi.reverse({
      project_id: props.projectId,
      target_total: targetTotal.value * 10000,
      other_cost: otherCost.value * 10000,
    });
    reverseResult.value = r;
    results.setReverseResult(r);
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "反算失败";
  } finally {
    loading.value = false;
  }
}

async function selectBand(band: "P10" | "P50" | "P90"): Promise<void> {
  selectedBand.value = band;
  // Persist to project — failures are non-critical (local state still updates).
  try {
    await projectsApi.patch(props.projectId, { selected_band: band });
  } catch (e: unknown) {
    // eslint-disable-next-line no-console
    console.warn("Failed to persist selected_band:", e);
  }
}

async function download(): Promise<void> {
  downloading.value = true;
  downloadError.value = null;
  try {
    await reportsApi.download(
      props.projectId,
      `${project.value?.name ?? "report"}.xlsx`,
      selectedBand.value,
    );
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

const reverseFillPending = ref(false);
const reverseFillMsg = ref("");
const reverseFillError = ref(false);

async function triggerReverseFill(): Promise<void> {
  reverseFillPending.value = true;
  reverseFillMsg.value = "";
  reverseFillError.value = false;
  try {
    const task = await aiTasksApi.create(props.projectId, "reverse_fill");
    await aiTasksApi.start(task.id);
    reverseFillError.value = false;
    reverseFillMsg.value = "已启动 AI 补全任务，请在 FP 编辑页的任务面板查看进度";
  } catch (e: unknown) {
    reverseFillError.value = true;
    reverseFillMsg.value = e instanceof Error ? e.message : "补全任务启动失败";
  } finally {
    reverseFillPending.value = false;
  }
}

function back(): void {
  router.push({ name: "fp-editor", params: { id: props.projectId } });
}

const hasForward = computed(() => forwardResult.value !== null);
const hasReverse = computed(() => reverseResult.value !== null);

// v2.2: forward 三档 tiers for ResultTrio
const PHASE_LABEL_MAP: Record<string, string> = {
  budget: "预算编制",
  bidding: "招投标",
  planning: "立项审批",
  change: "变更评估",
  settled: "结算审计",
};

const BAND_DETAIL_LABEL: Record<"P10" | "P50" | "P90", string> = {
  P10: "P10 乐观档",
  P50: "P50 推荐档",
  P90: "P90 保守档",
};

const forwardTiers = computed(() => {
  if (!forwardResult.value) return [];
  const r = forwardResult.value;
  return (["P10", "P50", "P90"] as const).map((k) => ({
    key: k,
    label:
      k === "P10"
        ? "乐观 · 行业最高效率"
        : k === "P50"
          ? "中位 · CSBMK 行业基准"
          : "保守 · 含返工/沟通损耗",
    cost: r.cost_total_yuan[k],
    recommended: k === "P50",
    unit: "yuan" as const,
    extras: [
      ["调整后规模 S", `${r.scale_adjusted.toFixed(2)} FP`],
      ["开发工作量", `${r.effort_dev_hours[k].toFixed(2)} 人时`],
      ["开发成本", `${Math.round(r.cost_dev_yuan[k]).toLocaleString()} 元`],
      ["运维工作量", `${r.effort_ops_hours[k].toFixed(2)} 人时`],
      ["运维成本", `${Math.round(r.cost_ops_yuan[k]).toLocaleString()} 元`],
      ["其他费用", `${(r.cost_other_yuan ?? 0).toLocaleString()} 元`],
    ] as Array<[string, string]>,
  }));
});

function fmtWan(n: number): string {
  return (n / 10000).toFixed(2);
}
</script>

<template>
  <section
    class="page hero-bg"
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
        返回
      </button>
      <div class="page-spacer" />
      <template v-if="project?.mode === 'reverse' && hasReverse">
        <button
          type="button"
          class="btn btn-ghost"
          :disabled="!hasReverse"
          @click="reverseCalc"
        >
          ↻ 重新反算
        </button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="downloading"
          @click="download"
        >
          {{ downloading ? "下载中…" : "下载 Excel" }}
        </button>
      </template>
      <p
        v-if="downloadError && project?.mode === 'reverse'"
        class="dl-error"
        role="alert"
        style="width: 100%; margin-top: 8px"
      >
        下载失败：{{ downloadError }}
      </p>
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

    <!-- v2.2: forward 结果区域 — ResultTrio + PipelineGrid + CostBar + ComplianceCard -->
    <div
      v-else-if="project?.mode === 'forward' && hasForward"
      class="forward-result"
    >
      <ResultTrio
        :tiers="forwardTiers"
        :selected-band="selectedBand"
        @select="selectBand"
      />

      <div class="section">
        <div class="section-head">
          <div class="section-title">计算路径详解 · {{ BAND_DETAIL_LABEL[selectedBand] }}</div>
          <div class="section-sub">附录 D 算例 · 黄金测试基准</div>
        </div>
        <div
          class="card"
          style="padding: 20px"
        >
          <PipelineGrid
            v-if="forwardResult!.trace"
            :trace="forwardResult!.trace"
            :phase-label="PHASE_LABEL_MAP[project!.phase] || project!.phase"
            :city-label="project!.city"
            :band="selectedBand"
            :effort-dev-hours="forwardResult!.effort_dev_hours"
            :cost-total-yuan="forwardResult!.cost_total_yuan"
          />
          <div
            v-else
            class="muted"
          >
            trace 数据待计算 — 点上方 "重新计算"
          </div>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1.4fr 1fr; gap: 16px; margin-top: 16px">
        <div
          class="card"
          style="padding: 20px"
        >
          <div style="display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 14px">
            <div class="section-title">成本构成分布</div>
            <span
              class="muted mono"
              style="font-size: 11px"
            >{{ selectedBand }} · 合计 {{ Math.round(forwardResult!.cost_total_yuan[selectedBand]).toLocaleString() }} 元</span>
          </div>
          <CostBar
            v-if="forwardResult!.composition"
            :composition="forwardResult!.composition"
          />
          <div
            v-else
            class="muted"
          >
            composition 数据待计算
          </div>
        </div>
        <ComplianceCard :p50-wan="fmtWan(forwardResult!.cost_total_yuan.P50)" />
        <!-- ComplianceCard always cites P50 as the compliance baseline per standard wording -->
      </div>
    </div>

    <div
      v-else-if="project?.mode === 'reverse'"
      class="reverse"
    >
      <div
        class="card"
        style="padding: 20px; margin-bottom: 16px"
      >
        <div
          class="section-title"
          style="margin-bottom: 14px"
        >
          反算输入
        </div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px">
          <div
            class="field"
            style="margin-bottom: 0"
          >
            <label class="field-label">目标总造价 (万元)</label>
            <input
              v-model.number="targetTotal"
              class="field-input mono"
              type="number"
              min="0"
            >
          </div>
          <div
            class="field"
            style="margin-bottom: 0"
          >
            <label class="field-label">其他费用 (万元)</label>
            <input
              v-model.number="otherCost"
              class="field-input mono"
              type="number"
              min="0"
            >
          </div>
          <div
            class="field"
            style="margin-bottom: 0"
          >
            <label class="field-label">可用预算 (万元)</label>
            <input
              class="field-input mono"
              :value="availableBudget"
              disabled
              style="background: var(--surface-sunken)"
            >
          </div>
        </div>
        <div style="margin-top: 14px; display: flex; gap: 8px">
          <button
            type="button"
            class="btn btn-primary"
            @click="reverseCalc"
          >
            反算
          </button>
        </div>
      </div>

      <template v-if="hasReverse">
        <!-- 成本拆分：单一规模下按生产率/费率反推的开发 / 运维占比 -->
        <div
          class="card"
          style="padding: 20px"
        >
          <div
            class="section-title"
            style="margin-bottom: 14px"
          >
            成本拆分（按规模反推的开发 / 运维占比 · 推荐档）
          </div>
          <div class="budget-split">
            <div class="budget-cell">
              <div class="budget-label">开发成本</div>
              <div class="budget-value">{{ fmtWan(reverseResult!.budget_for_dev) }} 万元</div>
              <div class="muted mono">{{ Math.round(reverseResult!.budget_for_dev).toLocaleString() }} 元</div>
            </div>
            <div class="budget-cell">
              <div class="budget-label">运维成本</div>
              <div class="budget-value">{{ fmtWan(reverseResult!.budget_for_ops) }} 万元</div>
              <div class="muted mono">{{ Math.round(reverseResult!.budget_for_ops).toLocaleString() }} 元</div>
            </div>
          </div>
        </div>

        <!-- 功能点规模三档（开发与运维共用同一规模）-->
        <div>
          <div
            class="section-title"
            style="margin-bottom: 10px"
          >
            功能点规模 · 反算三档
          </div>
          <ResultTrio :tiers="reverseTiers" />
        </div>

        <!-- 反算 UFP 三级模块树细化分摊 -->
        <div
          v-if="reverseResult!.module_allocation_tree && reverseResult!.module_allocation_tree.length"
          class="card"
          style="padding: 20px"
        >
          <div
            style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px"
          >
            <div class="section-title">反算 UFP 模块树细化分摊</div>
            <button
              type="button"
              data-testid="reverse-fill-btn"
              class="btn btn-primary btn-sm"
              :disabled="reverseFillPending"
              @click="triggerReverseFill"
            >
              {{ reverseFillPending ? "启动中…" : "按反算补全 FP" }}
            </button>
          </div>
          <div class="muted" style="font-size: 12px; margin-bottom: 12px">
            目标可承载 UFP <b class="mono">{{ reverseResult!.target_ufp.toFixed(2) }}</b>，
            沿 子系统 → 一级 → 二级 模块树逐层按现有 UFP 占比分摊。
            「按反算补全 FP」会让 AI 为有缺口的叶子模块生成功能点草稿（需人工审核后采纳）。
          </div>
          <div
            v-if="reverseFillMsg"
            class="banner"
            :class="reverseFillError ? 'banner-amber' : 'banner-green'"
            :role="reverseFillError ? 'alert' : 'status'"
            style="margin-bottom: 12px"
          >
            {{ reverseFillMsg }}
          </div>
          <table class="table">
            <thead>
              <tr>
                <th>模块层级</th>
                <th style="text-align: right">现有 UFP</th>
                <th style="text-align: right">分摊后 UFP</th>
                <th style="text-align: right">缺口 / 超出</th>
                <th style="text-align: right">占比</th>
              </tr>
            </thead>
            <tbody>
              <template
                v-for="sub in reverseResult!.module_allocation_tree"
                :key="sub.subsystem"
              >
                <tr class="tree-row-l0">
                  <td>{{ sub.subsystem }}</td>
                  <td class="mono" style="text-align: right">{{ sub.current_ufp.toFixed(2) }}</td>
                  <td class="mono" style="text-align: right">{{ sub.allocated_ufp.toFixed(2) }}</td>
                  <td
                    class="mono"
                    style="text-align: right"
                    :style="{ color: sub.delta_ufp >= 0 ? 'var(--green)' : 'var(--red)' }"
                  >{{ sub.delta_ufp >= 0 ? "+" : "" }}{{ sub.delta_ufp.toFixed(2) }}</td>
                  <td class="mono" style="text-align: right">{{ (sub.ratio * 100).toFixed(1) }}%</td>
                </tr>
                <template
                  v-for="l1 in sub.children"
                  :key="`${sub.subsystem}/${l1.l1_module}`"
                >
                  <tr class="tree-row-l1">
                    <td style="padding-left: 24px">{{ l1.l1_module }}</td>
                    <td class="mono" style="text-align: right">{{ l1.current_ufp.toFixed(2) }}</td>
                    <td class="mono" style="text-align: right">{{ l1.allocated_ufp.toFixed(2) }}</td>
                    <td
                      class="mono"
                      style="text-align: right"
                      :style="{ color: l1.delta_ufp >= 0 ? 'var(--green)' : 'var(--red)' }"
                    >{{ l1.delta_ufp >= 0 ? "+" : "" }}{{ l1.delta_ufp.toFixed(2) }}</td>
                    <td class="mono" style="text-align: right">{{ (l1.ratio * 100).toFixed(1) }}%</td>
                  </tr>
                  <tr
                    v-for="l2 in l1.children"
                    :key="`${sub.subsystem}/${l1.l1_module}/${l2.l2_module}`"
                    class="tree-row-l2"
                  >
                    <td style="padding-left: 48px" class="muted">{{ l2.l2_module }}</td>
                    <td class="mono" style="text-align: right">{{ l2.current_ufp.toFixed(2) }}</td>
                    <td class="mono" style="text-align: right; font-weight: 500">
                      {{ l2.allocated_ufp.toFixed(2) }}
                    </td>
                    <td
                      class="mono"
                      style="text-align: right"
                      :style="{ color: l2.delta_ufp >= 0 ? 'var(--green)' : 'var(--red)' }"
                    >{{ l2.delta_ufp >= 0 ? "+" : "" }}{{ l2.delta_ufp.toFixed(2) }}</td>
                    <td class="mono" style="text-align: right">{{ (l2.ratio * 100).toFixed(1) }}%</td>
                  </tr>
                </template>
              </template>
            </tbody>
          </table>
        </div>
      </template>

      <AllocatorPanel
        v-if="reverseResult && project"
        :reverse-result="reverseResult"
        :project-id="projectId"
        @allocated="onAllocated"
        @fp-updated="onFpUpdated"
      />

      <div
        v-if="fpUpdatedMsg"
        class="banner banner-green"
        role="status"
      >
        ✓ {{ fpUpdatedMsg }}
      </div>
    </div>

    <footer
      v-if="hasForward"
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
.forward-result {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.section {
  margin-top: 16px;
}
.section-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 10px;
}
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}
.section-sub {
  font-size: 11px;
  color: var(--text-3);
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}
.muted {
  color: var(--text-3);
  font-size: 12px;
}
.mono {
  font-family: var(--font-mono);
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
.budget-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}
.budget-cell {
  padding: var(--space-3) var(--space-4);
  background: var(--surface-sunken, var(--color-bg-hover));
  border: 1px solid var(--border, var(--color-border));
  border-radius: var(--radius-md);
}
.budget-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: 500;
}
.budget-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--text, var(--color-text));
  margin: 4px 0 2px;
}
.tree-row-l0 td {
  background: var(--color-bg-hover, #f8fafc);
  font-weight: 600;
}
.tree-row-l1 td {
  font-weight: 500;
}
.tree-row-l2 td {
  font-size: 12px;
}
</style>
