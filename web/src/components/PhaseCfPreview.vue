<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  phase: string;
  cf: Record<string, number>;
}>();
defineEmits<{ (e: "update:phase", v: string): void }>();

const PHASE_LABELS: Record<string, string> = {
  budget: "预算",
  bidding: "招标",
  planning: "立项",
  change: "变更",
  settled: "结算",
};

const PHASE_HINTS: Record<string, string> = {
  budget: "项目尚未立项 — 预算阶段最大不确定性。",
  bidding: "已经发标 — 不确定性中等。",
  planning: "立项完成 — 已收敛。",
  change: "变更过程中 — 二次估算。",
  settled: "项目结束 — 数值已确定。",
};

const currentCf = computed(() => props.cf?.[props.phase] ?? 1.0);
</script>

<template>
  <div>
    <div class="phase-grid">
      <label
        v-for="key in Object.keys(PHASE_LABELS)"
        :key="key"
        class="phase-card"
        :data-active="key === phase"
        :data-testid="`phase-card-${key}`"
      >
        <input
          type="radio"
          name="phase"
          :value="key"
          :checked="key === phase"
          @change="$emit('update:phase', key)"
        >
        <strong>{{ PHASE_LABELS[key] }}</strong>
        <span class="cf">CF = {{ (cf?.[key] ?? 1.0).toFixed(2) }}</span>
        <p>{{ PHASE_HINTS[key] }}</p>
      </label>
    </div>
    <div class="phase-summary">
      您选择的阶段对应的 CF 调整因子 = <strong>{{ currentCf.toFixed(2) }}</strong>。
      它会作为本项目所有计算的乘数。
    </div>
  </div>
</template>

<style scoped>
.phase-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 8px;
}
.phase-card {
  display: block;
  padding: 12px;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 6px;
  cursor: pointer;
}
.phase-card[data-active="true"] {
  border-color: var(--color-primary, #165DFF);
  background: rgba(22, 93, 255, 0.06);
}
.phase-card input[type="radio"] {
  margin-right: 6px;
}
.phase-card strong {
  display: block;
  margin: 4px 0;
}
.phase-card .cf {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-muted, #6b7280);
}
.phase-card p {
  font-size: 12px;
  color: var(--color-text-muted, #6b7280);
  margin: 4px 0 0;
}
.phase-summary {
  margin-top: 16px;
  padding: 12px;
  background: rgba(22, 93, 255, 0.06);
  border-radius: 6px;
}
</style>
