<script setup lang="ts">
interface Tier {
  key: "P10" | "P50" | "P90";
  label: string;
  cost: number;
  hours?: number;
  fp?: number;
  recommended?: boolean;
  unit?: "yuan" | "fp";
  extras?: Array<[string, string]>;
}

const props = defineProps<{
  tiers: Tier[];
  selectedBand?: "P10" | "P50" | "P90";
}>();

const emit = defineEmits<{
  (e: "select", band: "P10" | "P50" | "P90"): void;
}>();

function selectBand(key: "P10" | "P50" | "P90") {
  emit("select", key);
}

function onKeydown(event: KeyboardEvent, key: "P10" | "P50" | "P90") {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    selectBand(key);
  }
}

function fmtMoney(n: number): string {
  return Math.round(n).toLocaleString("zh-CN");
}
function fmtWan(n: number): string {
  return (n / 10000).toFixed(2);
}
</script>

<template>
  <div class="result-trio">
    <div
      v-for="t in tiers"
      :key="t.key"
      class="result-card"
      :class="{
        recommended: t.recommended,
        selected: t.key === selectedBand,
      }"
      role="button"
      tabindex="0"
      :aria-pressed="t.key === selectedBand"
      :data-testid="`tier-card-${t.key}`"
      :data-selected="t.key === selectedBand ? 'true' : 'false'"
      @click="selectBand(t.key)"
      @keydown="onKeydown($event, t.key)"
    >
      <div v-if="t.key === selectedBand" class="result-card-selected-mark" aria-hidden="true">✓</div>
      <div v-if="t.recommended" class="result-card-pill">推荐 · P50</div>
      <div class="result-card-tag">{{ t.key }}</div>
      <div class="result-card-name">{{ t.label }}</div>
      <div class="result-card-amt" :class="{ dimmed: !t.recommended && t.key !== selectedBand }">
        <template v-if="t.unit === 'fp'">
          {{ t.fp?.toFixed(2) }}<span class="unit">FP</span>
        </template>
        <template v-else>
          ¥{{ fmtMoney(t.cost) }}<span class="unit">元</span>
        </template>
      </div>
      <div class="muted mono" style="font-size: 12px">
        <template v-if="t.unit === 'fp'">≈ {{ t.fp ? Math.round(t.fp / 30) : '—' }} 个模块</template>
        <template v-else>= {{ fmtWan(t.cost) }} 万元</template>
      </div>
      <div v-if="t.extras && t.extras.length" class="result-card-extras">
        <div v-for="(row, i) in t.extras" :key="i" class="result-card-row">
          <span>{{ row[0] }}</span>
          <span class="v">{{ row[1] }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.result-trio { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 16px; }
.result-card {
  position: relative;
  padding: 22px 22px 20px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: box-shadow 120ms ease, border-color 120ms ease;
  outline: none;
}
.result-card:hover {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px color-mix(in oklch, var(--accent) 15%, transparent);
}
.result-card:focus-visible {
  box-shadow: 0 0 0 3px var(--accent-soft), 0 0 0 5px var(--accent);
}
.result-card.recommended {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}
.result-card.selected {
  border-color: var(--accent);
  box-shadow: 0 0 0 4px var(--accent);
  background: color-mix(in oklch, var(--accent) 6%, var(--surface));
}
.result-card.selected.recommended {
  box-shadow: 0 0 0 4px var(--accent);
}
.result-card-selected-mark {
  position: absolute;
  top: 10px;
  right: 14px;
  width: 20px;
  height: 20px;
  background: var(--accent);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
}
.result-card-pill {
  position: absolute; top: -12px; left: 22px;
  padding: 4px 10px;
  background: var(--accent); color: #fff;
  font-size: 11px; font-weight: 600;
  border-radius: 10px;
}
.result-card-tag {
  font-family: var(--font-mono); font-size: 11px; font-weight: 600;
  color: var(--text-3);
  padding: 2px 8px;
  display: inline-block;
  border: 1px solid var(--border);
  border-radius: 4px;
  margin-bottom: 12px;
}
.result-card-name { font-size: 12px; color: var(--text-2); margin-bottom: 14px; }
.result-card-amt {
  font-family: var(--font-mono);
  font-size: 32px; font-weight: 600; letter-spacing: -0.02em;
  color: var(--accent);
  line-height: 1;
}
.result-card-amt.dimmed { color: var(--text-2); font-size: 26px; }
.result-card-amt .unit { font-size: 14px; font-weight: 400; color: var(--text-3); margin-left: 4px; }
.result-card-extras { margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--border); }
.result-card-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px; }
.result-card-row span:first-child { color: var(--text-3); }
.result-card-row .v { font-family: var(--font-mono); color: var(--text); }
</style>
