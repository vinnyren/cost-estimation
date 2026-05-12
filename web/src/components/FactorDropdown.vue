<script setup lang="ts">
/**
 * FactorDropdown — Wizard 因子配置 dropdown。用户给每个因子选一个 level，
 * 同组所有因子的 multiplier 链式相乘 = 该组（dev / ops）的总调整系数。
 *
 * 与 FactorTable 的区别：FactorTable 改的是参数值本身（落库 override），
 * 这里只在 form 上记选择，submit 时进 projectsApi.create 的
 * factors_dev / factors_ops payload。
 *
 * 关联：ProjectWizard step 5（开发因子）与 step 6（运维因子）。
 *
 * v2.5：增加 meta prop，接 /api/params/factor-meta 返回的中文 label/description/options。
 */
import type { FactorMeta } from "@/api/factorMeta";

interface FactorLevel {
  multiplier: number;
  description?: string;
}

interface FactorDef {
  name: string;
  label: string;
  levels: Record<string, FactorLevel>;
}

defineProps<{
  factor: FactorDef;
  modelValue: string | undefined;
  meta?: FactorMeta;
}>();

defineEmits<{
  (e: "update:modelValue", v: string): void;
}>();
</script>

<template>
  <label
    class="factor-dd"
    :data-factor="factor.name"
  >
    <span class="lbl">
      {{ meta?.label ?? factor.label }}
      <span
        v-if="meta?.description"
        class="muted"
        :title="meta.description"
        style="cursor: help; margin-left: 4px"
      >ⓘ</span>
      <span class="key">({{ factor.name }})</span>
    </span>
    <select
      :value="modelValue ?? ''"
      @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
    >
      <option
        value=""
        disabled
      >
        请选择
      </option>
      <option
        v-for="(lvl, key) in factor.levels"
        :key="String(key)"
        :value="String(key)"
        :title="meta?.options?.[String(key)]?.description ?? lvl.description"
      >
        {{ meta?.options?.[String(key)]?.label ?? key }} — ×{{ lvl.multiplier.toFixed(2) }}<span v-if="!meta?.options?.[String(key)] && lvl.description"> · {{ lvl.description }}</span>
      </option>
    </select>
  </label>
</template>

<style scoped>
.factor-dd {
  display: block;
  margin-bottom: var(--space-3, 12px);
}
.lbl {
  display: block;
  font-size: var(--font-size-sm, 13px);
  font-weight: 500;
  margin-bottom: var(--space-1, 4px);
  color: var(--color-text-body);
}
.key {
  font-weight: 400;
  color: var(--color-text-muted, #6b7280);
  margin-left: 4px;
}
.muted {
  font-weight: 400;
  color: var(--color-text-muted, #6b7280);
  font-size: var(--font-size-xs, 12px);
}
.factor-dd select {
  width: 100%;
  padding: var(--space-1, 6px) var(--space-2, 8px);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: var(--radius-md, 4px);
  background: var(--color-bg, #fff);
  font-size: var(--font-size-sm, 14px);
  color: var(--color-text-body);
}
.factor-dd select:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 1px;
}
</style>
