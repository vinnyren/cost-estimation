<script setup lang="ts">
defineProps<{
  city: string | null;
  industry: string | null;
  phase: string | null;
  view: "table" | "card";
  total: number;
  filtered: number;
}>();

const emit = defineEmits<{
  "update:city": [v: string | null];
  "update:industry": [v: string | null];
  "update:phase": [v: string | null];
  "update:view": [v: "table" | "card"];
}>();

const CITIES = ["全部", "北京", "上海", "深圳", "杭州", "苏州", "南京", "成都", "武汉"];
const INDUSTRIES = ["全部", "电子政务", "金融", "电信", "制造", "能源", "交通"];
const PHASES = [
  { value: "", label: "全部" },
  { value: "budget", label: "预算编制" },
  { value: "bidding", label: "招投标" },
  { value: "planning", label: "立项审批" },
  { value: "change", label: "变更评估" },
  { value: "settled", label: "结算审计" },
];

function setVal(k: "city" | "industry" | "phase", v: string) {
  const out = v === "全部" || v === "" ? null : v;
  if (k === "city") emit("update:city", out);
  if (k === "industry") emit("update:industry", out);
  if (k === "phase") emit("update:phase", out);
}
</script>

<template>
  <div class="toolbar">
    <select class="field-select compact" :value="city ?? '全部'" @change="setVal('city', ($event.target as HTMLSelectElement).value)">
      <option v-for="c in CITIES" :key="c" :value="c">城市：{{ c }}</option>
    </select>
    <select class="field-select compact" :value="industry ?? '全部'" @change="setVal('industry', ($event.target as HTMLSelectElement).value)">
      <option v-for="i in INDUSTRIES" :key="i" :value="i">行业：{{ i }}</option>
    </select>
    <select class="field-select compact" :value="phase ?? ''" @change="setVal('phase', ($event.target as HTMLSelectElement).value)">
      <option v-for="p in PHASES" :key="p.value" :value="p.value">阶段：{{ p.label }}</option>
    </select>
    <div style="flex: 1" />
    <div class="seg">
      <button :class="{ active: view === 'table' }" @click="emit('update:view', 'table')" aria-label="表格视图">⊞</button>
      <button :class="{ active: view === 'card' }" @click="emit('update:view', 'card')" aria-label="卡片视图">▦</button>
    </div>
    <span class="muted" style="font-size: 12px">{{ filtered }} / {{ total }}</span>
  </div>
</template>

<style scoped>
.field-select.compact { width: auto; height: 32px; font-size: 12px; padding: 0 28px 0 10px; }
</style>
