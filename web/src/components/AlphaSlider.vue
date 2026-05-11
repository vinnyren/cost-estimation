<script setup lang="ts">
/**
 * AlphaSlider — 开发 / 运维占比 α 滑块。
 *
 * 仅在 project_type = "dev_and_ops" 时使用：α 表示开发工作量占总成本比例，
 * (1 − α) 即运维占比。range 限制 0.5–1.0 是项目经验值：低于 0.5 的开发占比
 * 在企业 IT 项目中罕见，刻意收窄区间避免误操作。
 *
 * 关联：ProjectWizard step 2；submit 时 v-model 写回 form.alpha，
 * 进而落到 projectsApi.create 的 alpha_dev 字段。
 */
import { computed } from "vue";

const props = defineProps<{
  modelValue: number;
}>();
const emit = defineEmits<{
  (e: "update:modelValue", v: number): void;
}>();

const value = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});
// 派生展示用运维占比；保留 toFixed(2) 避免 0.7 + 0.1 浮点抖动 (0.7999... 之类)
const opsShare = computed(() => (1 - value.value).toFixed(2));
</script>

<template>
  <div class="alpha-slider">
    <label class="title">α (开发占总成本比例)</label>
    <div class="control">
      <input
        v-model.number="value"
        type="range"
        min="0.5"
        max="1.0"
        step="0.05"
        aria-label="开发占比 α"
      >
      <span class="value">α = {{ value.toFixed(2) }}</span>
    </div>
    <p class="hint">
      运维占比 = 1 − α = <strong>{{ opsShare }}</strong>。
      α 越大，开发权重越高；α=1.0 等价于"仅开发"。
    </p>
  </div>
</template>

<style scoped>
.alpha-slider {
  padding: var(--space-3, 12px);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: var(--radius-md, 6px);
}
.title {
  font-weight: 600;
  display: block;
  margin-bottom: var(--space-2, 8px);
}
.control {
  display: flex;
  align-items: center;
  gap: var(--space-3, 12px);
}
.control input[type="range"] {
  flex: 1;
}
.value {
  font-variant-numeric: tabular-nums;
  min-width: 80px;
  text-align: right;
}
.hint {
  color: var(--color-text-muted, #6b7280);
  font-size: var(--font-size-xs, 12px);
  margin: var(--space-2, 8px) 0 0;
}
</style>
