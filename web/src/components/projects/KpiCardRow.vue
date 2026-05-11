<script setup lang="ts">
import type { ProjectStats } from "@/api/stats";

defineProps<{
  stats: ProjectStats;
  activeFilter: string;
}>();
const emit = defineEmits<{ filter: [key: string] }>();

interface CardDef {
  key: string;
  label: string;
  icon: string;
  countKey: "total" | "draft" | "in_progress" | "archived";
}

const cards: CardDef[] = [
  { key: "全部", label: "全部", icon: "folder", countKey: "total" },
  { key: "草稿", label: "草稿", icon: "edit", countKey: "draft" },
  { key: "计算中", label: "计算中 / 已计算", icon: "refresh", countKey: "in_progress" },
  { key: "已归档", label: "已归档", icon: "folder", countKey: "archived" },
];

function fmtWan(n: number): string {
  return (n / 10000).toFixed(2);
}
</script>

<template>
  <div class="kpi-row">
    <button
      v-for="c in cards"
      :key="c.key"
      class="kpi-card"
      :class="{ active: activeFilter === c.key }"
      @click="emit('filter', c.key)"
    >
      <div class="kpi-icon">📁</div>
      <div>
        <div class="kpi-label">{{ c.label }}</div>
        <div class="kpi-val mono">{{ stats.counts[c.countKey] }}</div>
      </div>
    </button>
    <div class="kpi-card kpi-summary">
      <div>
        <div class="kpi-label">本月总造价（P50）</div>
        <div class="kpi-val mono">¥{{ fmtWan(stats.monthly_p50_sum) }}<span class="kpi-unit">万</span></div>
      </div>
      <div class="kpi-trend" :class="stats.monthly_growth_pct >= 0 ? 'up' : 'down'">
        {{ stats.monthly_growth_pct >= 0 ? '↑' : '↓' }} {{ Math.abs(stats.monthly_growth_pct) }}%
      </div>
    </div>
  </div>
</template>

<style scoped>
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr) 1.5fr;
  gap: 12px;
  margin-bottom: 16px;
}
.kpi-card {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 16px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  text-align: left;
  cursor: pointer;
}
.kpi-card.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-soft);
}
.kpi-icon {
  width: 32px; height: 32px; border-radius: var(--radius);
  background: var(--accent-soft); color: var(--accent);
  display: grid; place-items: center;
}
.kpi-label { font-size: 11px; color: var(--text-3); }
.kpi-val { font-size: 22px; font-weight: 600; letter-spacing: -0.02em; color: var(--text); }
.kpi-unit { font-size: 12px; font-weight: 400; color: var(--text-3); margin-left: 2px; }
.kpi-summary {
  justify-content: space-between;
  background: linear-gradient(135deg, var(--accent-soft), var(--surface));
  border-color: var(--accent-soft-strong);
  cursor: default;
}
.kpi-trend.up { color: var(--green); }
.kpi-trend.down { color: var(--red); }
</style>
