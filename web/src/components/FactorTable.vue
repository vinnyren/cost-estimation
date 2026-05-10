<script setup lang="ts">
import { computed } from "vue";

interface Level {
  multiplier: number;
  description?: string;
}

interface FactorDef {
  name: string;
  label: string;
  levels: Record<string, Level>;
}

const props = defineProps<{
  factor: FactorDef;
  scope: "global" | string;
}>();

const emit = defineEmits<{
  (e: "update:multiplier", v: { levelKey: string; value: number }): void;
}>();

const rows = computed(() =>
  Object.entries(props.factor.levels).map(([k, v]) => ({
    key: k,
    multiplier: v.multiplier,
    description: v.description ?? "",
  })),
);

function onInput(levelKey: string, ev: Event): void {
  const raw = (ev.target as HTMLInputElement).value;
  const v = parseFloat(raw);
  if (!isNaN(v) && isFinite(v) && v >= 0) {
    emit("update:multiplier", { levelKey, value: v });
  }
}
</script>

<template>
  <div
    class="factor-card"
    :data-factor="factor.name"
  >
    <h4 class="factor-title">
      {{ factor.label }}
      <span class="factor-key">({{ factor.name }})</span>
    </h4>
    <table class="factor-table">
      <thead>
        <tr>
          <th>级别</th>
          <th>说明</th>
          <th>系数</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in rows"
          :key="row.key"
          :data-level="row.key"
        >
          <td>{{ row.key }}</td>
          <td class="desc-cell">
            {{ row.description }}
          </td>
          <td class="mult-cell">
            <input
              type="number"
              step="0.01"
              min="0"
              :value="row.multiplier.toFixed(2)"
              :aria-label="`${factor.label} ${row.key} 系数`"
              @change="onInput(row.key, $event)"
            >
            <span
              class="mult-sr"
              aria-hidden="true"
            >{{ row.multiplier.toFixed(2) }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.factor-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 6px);
  padding: var(--space-3);
  margin-bottom: var(--space-3);
  background: var(--color-bg-elevated, #fff);
}
.factor-title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  margin: 0 0 var(--space-2) 0;
  color: var(--color-text-body);
}
.factor-key {
  font-weight: 400;
  color: var(--color-text-muted);
  margin-left: var(--space-2);
  font-size: var(--font-size-xs);
}
.factor-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}
.factor-table th,
.factor-table td {
  padding: var(--space-1, 4px) var(--space-2);
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}
.factor-table th {
  color: var(--color-text-muted);
  font-weight: 500;
  font-size: var(--font-size-xs);
}
.factor-table tr:last-child td {
  border-bottom: none;
}
.desc-cell {
  color: var(--color-text-muted);
}
.factor-table input {
  width: 80px;
  padding: 2px var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm, 3px);
  font-family: inherit;
  font-size: inherit;
  color: var(--color-text-body);
}
.factor-table input:focus {
  outline: none;
  border-color: var(--color-primary);
}
.mult-sr {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
