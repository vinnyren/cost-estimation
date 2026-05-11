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

const props = defineProps<{ trace: PipelineTrace; phaseLabel: string; cityLabel: string }>();

const steps = computed(() => [
  { tag: "US", label: "未调整规模", val: props.trace.us.toFixed(2), unit: "FP", note: "Σ FP[i].us" },
  { tag: "×", label: "阶段调整因子 CF", val: props.trace.cf.toFixed(2), unit: "", note: props.phaseLabel },
  { tag: "S", label: "调整后规模", val: props.trace.s_adjusted.toFixed(2), unit: "FP", note: "US × CF", highlight: true },
  { tag: "÷", label: "PDR P50", val: props.trace.pdr_p50.toFixed(2), unit: "FP/PM", note: "CSBMK §4.1" },
  { tag: "×", label: "开发因子乘积", val: props.trace.dev_factor.toFixed(2), unit: "", note: "5 项" },
  { tag: "EFF", label: "开发工作量", val: props.trace.eff_pm_p50.toFixed(2), unit: "人月", note: `= ${props.trace.eff_hours_p50.toFixed(0)} 人时`, highlight: true },
  { tag: "×", label: `F_city (${props.cityLabel})`, val: props.trace.f_city.toLocaleString(), unit: "元/PM", note: "" },
  { tag: "+", label: "运维 + 其他费", val: Math.round(props.trace.ops_plus_other).toLocaleString(), unit: "元", note: "" },
  { tag: "=", label: "P50 总造价", val: Math.round(props.trace.total_p50).toLocaleString(), unit: "元", note: `≈ ${(props.trace.total_p50 / 10000).toFixed(2)} 万元`, final: true },
]);
</script>

<template>
  <div class="pipeline-grid">
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
