<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  label: string;
  modelValue: number | string;
  defaultValue: number | string;
  step?: number;
  min?: number;
  max?: number;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: number | string): void;
  (e: "reset"): void;
}>();

const isOverridden = computed(() => props.modelValue !== props.defaultValue);

function onInput(e: Event): void {
  const target = e.target as HTMLInputElement;
  const v = target.type === "number" ? Number(target.value) : target.value;
  emit("update:modelValue", v);
}

function reset(): void {
  emit("update:modelValue", props.defaultValue);
  emit("reset");
}
</script>

<template>
  <div
    class="field"
    :data-overridden="isOverridden"
  >
    <label>
      <span class="label">{{ label }}</span>
      <input
        :value="modelValue"
        type="number"
        :step="step ?? 0.01"
        :min="min"
        :max="max"
        :aria-describedby="isOverridden ? `${label}-override-note` : undefined"
        @input="onInput"
      >
    </label>
    <span
      v-if="isOverridden"
      :id="`${label}-override-note`"
      data-test="override-badge"
      class="badge"
      role="status"
    >自定义</span>
    <button
      v-if="isOverridden"
      type="button"
      data-test="reset-btn"
      class="reset"
      :aria-label="`恢复 ${label} 为默认值`"
      @click="reset"
    >
      ↺
    </button>
  </div>
</template>

<style scoped>
.field {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  position: relative;
  transition: background var(--duration-fast) var(--ease-out);
}
.field[data-overridden="true"] {
  background: var(--color-warn-bg);
  border-left: 3px solid var(--color-warn-stripe);
}
.label {
  font-size: 14px;
  min-width: 100px;
}
input {
  min-height: 44px;
  padding: 0 var(--space-2);
  border-radius: var(--radius-sm);
}
.badge {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 999px;
  background: var(--color-warn-stripe);
  color: white;
}
.reset {
  min-height: 44px;
  min-width: 44px;
  padding: 0;
  background: transparent;
  border: 1px solid oklch(75% 0 0);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
</style>
