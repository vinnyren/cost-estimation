<script setup lang="ts">
import { computed } from "vue";

interface Composition {
  dev_labor: number;
  ops_labor: number;
  other: number;
  indirect: number;
}

const props = defineProps<{ composition: Composition }>();

const items = computed(() => [
  { name: "开发人工", value: props.composition.dev_labor, color: "#2563EB" },
  { name: "运维人工", value: props.composition.ops_labor, color: "#7C3AED" },
  { name: "其他费用", value: props.composition.other, color: "#0E7490" },
  { name: "间接/管理", value: props.composition.indirect, color: "#94A3B8" },
].filter((it) => it.value > 0));

const total = computed(() => items.value.reduce((a, b) => a + b.value, 0));

function fmtMoney(n: number): string {
  return Math.round(n).toLocaleString("zh-CN");
}
function pct(v: number): number {
  if (total.value === 0) return 0;
  return (v / total.value) * 100;
}
</script>

<template>
  <div class="cost-bar">
    <div class="cost-bar-track">
      <div
        v-for="it in items"
        :key="it.name"
        :title="`${it.name} ¥${fmtMoney(it.value)}`"
        class="cost-bar-seg"
        :style="{ background: it.color, width: `${pct(it.value)}%` }"
      >
        <span v-if="pct(it.value) > 8">{{ pct(it.value).toFixed(1) }}%</span>
      </div>
    </div>
    <div class="cost-bar-legend">
      <div v-for="it in items" :key="it.name" class="cost-bar-row">
        <span class="cost-bar-dot" :style="{ background: it.color }" />
        <span class="cost-bar-name">{{ it.name }}</span>
        <span class="mono">¥{{ fmtMoney(it.value) }}</span>
        <span class="muted mono cost-bar-pct">{{ pct(it.value).toFixed(1) }}%</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cost-bar-track {
  display: flex; height: 28px;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}
.cost-bar-seg {
  display: grid; place-items: center;
  color: white; font-size: 11px; font-weight: 500;
}
.cost-bar-legend { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 14px; }
.cost-bar-row { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.cost-bar-dot { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
.cost-bar-name { flex: 1; }
.cost-bar-pct { width: 50px; text-align: right; }
</style>
