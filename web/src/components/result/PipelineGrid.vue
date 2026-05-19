<script setup lang="ts">
import { computed } from "vue";

interface PipelineTrace {
  us: number;
  cf: number;
  s_adjusted: number;
  pdr_p50: number;
  dev_factor: number;
  eff_pm_p50: number;
  eff_hours_p50: number;
  f_city: number;
  ops_plus_other: number;
  total_p50: number;
}

const props = defineProps<{
  trace: PipelineTrace;
  phaseLabel: string;
  cityLabel: string;
  /** Selected band for display — defaults to P50 */
  band?: "P10" | "P50" | "P90";
  /** Per-band effort in person-hours (from ForwardResult.effort_dev_hours) */
  effortDevHours?: { P10: number; P50: number; P90: number };
  /** Per-band total cost in yuan (from ForwardResult.cost_total_yuan) */
  costTotalYuan?: { P10: number; P50: number; P90: number };
}>();

const BAND_LABEL: Record<string, string> = {
  P10: "P10 乐观档",
  P50: "P50 推荐档",
  P90: "P90 保守档",
};

const activeBand = computed(() => props.band ?? "P50");

/** PDR scales inversely with effort from P50 baseline */
const pdrForBand = computed(() => {
  if (activeBand.value === "P50" || !props.effortDevHours) {
    return props.trace.pdr_p50;
  }
  // PDR = S / EFF_pm. EFF_pm = effort_hours / 21.75 (approx workdays/month).
  // We keep the same S_adjusted, so PDR scales inversely with EFF.
  const effPmP50 = props.trace.eff_pm_p50;
  if (effPmP50 === 0) return props.trace.pdr_p50;
  const effPmBand = props.effortDevHours[activeBand.value] / (props.trace.eff_hours_p50 / effPmP50);
  return props.trace.pdr_p50 * (effPmP50 / effPmBand);
});

/** Effort in person-months for selected band */
const effPmForBand = computed(() => {
  if (activeBand.value === "P50" || !props.effortDevHours) {
    return props.trace.eff_pm_p50;
  }
  const effPmP50 = props.trace.eff_pm_p50;
  const effHoursP50 = props.trace.eff_hours_p50;
  if (effHoursP50 === 0) return effPmP50;
  const ratio = props.effortDevHours[activeBand.value] / props.effortDevHours["P50"];
  return effPmP50 * ratio;
});

/** Effort in person-hours for selected band */
const effHoursForBand = computed(() => {
  if (activeBand.value === "P50" || !props.effortDevHours) {
    return props.trace.eff_hours_p50;
  }
  return props.effortDevHours[activeBand.value];
});

/** Total cost in yuan for selected band */
const totalForBand = computed(() => {
  if (activeBand.value === "P50" || !props.costTotalYuan) {
    return props.trace.total_p50;
  }
  return props.costTotalYuan[activeBand.value];
});

const bandLabel = computed(() => BAND_LABEL[activeBand.value] ?? activeBand.value);

const steps = computed(() => [
  { tag: "US", label: "未调整规模", val: props.trace.us.toFixed(2), unit: "FP", note: "Σ FP[i].us" },
  { tag: "×", label: "阶段调整因子 CF", val: props.trace.cf.toFixed(2), unit: "", note: props.phaseLabel },
  { tag: "S", label: "调整后规模", val: props.trace.s_adjusted.toFixed(2), unit: "FP", note: "US × CF", highlight: true },
  { tag: "÷", label: `PDR ${activeBand.value}`, val: pdrForBand.value.toFixed(2), unit: "FP/PM", note: "CSBMK §4.1" },
  { tag: "×", label: "开发因子乘积", val: props.trace.dev_factor.toFixed(2), unit: "", note: "5 项" },
  { tag: "EFF", label: "开发工作量", val: effPmForBand.value.toFixed(2), unit: "人月", note: `= ${effHoursForBand.value.toFixed(0)} 人时`, highlight: true },
  { tag: "×", label: `F_city (${props.cityLabel})`, val: props.trace.f_city.toLocaleString(), unit: "元/PM", note: "" },
  { tag: "+", label: "运维 + 其他费", val: Math.round(props.trace.ops_plus_other).toLocaleString(), unit: "元", note: "" },
  { tag: "=", label: `${activeBand.value} 总造价`, val: Math.round(totalForBand.value).toLocaleString(), unit: "元", note: `≈ ${(totalForBand.value / 10000).toFixed(2)} 万元`, final: true },
]);
</script>

<template>
  <div class="pipeline-grid">
    <div class="pipeline-band-label">{{ bandLabel }}</div>
    <div
      v-for="(s, i) in steps"
      :key="i"
      class="pipeline-cell"
      :class="{ highlight: s.highlight, final: s.final }"
    >
      <div class="pipeline-head">
        <span class="pipeline-tag mono">{{ s.tag }}</span>
        <span class="muted" style="font-size: 11px">{{ s.label }}</span>
      </div>
      <div class="pipeline-val mono" :class="{ final: s.final }">
        {{ s.val }}<span class="unit">{{ s.unit }}</span>
      </div>
      <div v-if="s.note" class="muted mono" style="font-size: 10px; margin-top: 2px">{{ s.note }}</div>
    </div>
  </div>
</template>

<style scoped>
.pipeline-band-label {
  grid-column: 1 / -1;
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  margin-bottom: 4px;
  padding: 2px 0;
}
.pipeline-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
}
.pipeline-cell {
  padding: 12px 14px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  position: relative;
}
.pipeline-cell.highlight {
  background: var(--accent-soft);
  border-color: var(--accent-soft-strong);
}
.pipeline-cell.final {
  background: var(--accent-soft);
  border-color: var(--accent);
}
.pipeline-head { display: flex; align-items: baseline; gap: 8px; }
.pipeline-tag {
  font-size: 11px; font-weight: 600;
  padding: 1px 6px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text-3);
}
.pipeline-cell.final .pipeline-tag { color: var(--accent); border-color: var(--accent); }
.pipeline-val {
  font-size: 18px; font-weight: 600;
  margin-top: 6px;
  letter-spacing: -0.01em;
  color: var(--text);
}
.pipeline-val.final { font-size: 22px; color: var(--accent); }
.pipeline-val .unit { font-size: 12px; font-weight: 400; color: var(--text-3); margin-left: 4px; }
</style>
