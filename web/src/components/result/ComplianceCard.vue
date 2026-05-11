<script setup lang="ts">
const COMPLIANCE = [
  ["GB/T 36964-2018", "§7.2 PDR 公式 · 三档行业基准"],
  ["T/CCUA 005-2024", "附录 D 算例 · 黄金测试基准"],
  ["GB/T 28827.7-2022", "§6 运维 11 项因子"],
  ["CSBMK®-202510", "1500+ 在网项目统计"],
];

defineProps<{ p50Wan: string }>();
</script>

<template>
  <div class="card compliance-card">
    <div class="section-title" style="margin-bottom: 14px">合规说明</div>
    <div style="display: grid; gap: 10px">
      <div v-for="row in COMPLIANCE" :key="row[0]" class="compliance-row">
        <span class="compliance-check">✓</span>
        <div>
          <div class="mono"><b>{{ row[0] }}</b></div>
          <div class="muted">{{ row[1] }}</div>
        </div>
      </div>
    </div>
    <div class="compliance-quote">
      <b>💡 报告话术：</b>本项目 P50 推荐造价 <span class="mono">{{ p50Wan }} 万元</span>；
      P10/P90 为基于 CSBMK®-202510 行业生产率分布的敏感度边界，<b>非团队承诺值</b>。
    </div>
  </div>
</template>

<style scoped>
.compliance-card { padding: 20px; }
.compliance-row { display: flex; gap: 10px; font-size: 12px; padding: 6px 0; border-bottom: 1px dashed var(--border); }
.compliance-row:last-child { border-bottom: 0; }
.compliance-check { color: var(--green); margin-top: 2px; }
.compliance-quote {
  margin-top: 14px; padding: 10px;
  background: var(--surface-sunken);
  border-radius: 6px;
  font-size: 11px; line-height: 1.6;
  color: var(--text-2);
}
</style>
