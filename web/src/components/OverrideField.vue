<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    label: string;
    modelValue: number | string;
    defaultValue: number | string;
    overridden?: boolean;
    step?: number;
    min?: number;
    max?: number;
  }>(),
  { overridden: undefined, step: undefined, min: undefined, max: undefined },
);

const emit = defineEmits<{
  (e: "update:modelValue", v: number | string): void;
  (e: "reset"): void;
}>();

const isOverridden = computed(() =>
  props.overridden ?? (props.modelValue !== props.defaultValue),
);

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
    <label class="field-row">
      <span
        v-if="label"
        class="label"
      >{{ label }}</span>
      <input
        :value="modelValue"
        type="number"
        :step="step ?? 0.01"
        :min="min"
        :max="max"
        :aria-label="label || undefined"
        :aria-describedby="isOverridden ? `${label}-override-note` : undefined"
        @input="onInput"
      >
    </label>
    <div
      v-if="isOverridden"
      class="badges"
    >
      <span
        :id="`${label}-override-note`"
        data-test="override-badge"
        class="badge badge-warning"
        role="status"
      >自定义</span>
      <button
        type="button"
        data-test="reset-btn"
        class="reset"
        :aria-label="`恢复 ${label} 为默认值`"
        @click="reset"
      >
        ↺
      </button>
    </div>
  </div>
</template>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  border-left: 3px solid transparent;
  transition: background var(--duration-fast) var(--ease-out),
              border-color var(--duration-fast) var(--ease-out);
}
.field[data-overridden="true"] {
  background: var(--color-warning-bg);
  border-left-color: var(--color-warning);
}
.field-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: 500;
}
.field input {
  width: 100%;
}
.field[data-overridden="true"] input {
  border-color: var(--color-warning);
}
.badges {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-1);
}
.reset {
  height: 24px;
  width: 24px;
  padding: 0;
  background: transparent;
  border: 1px solid var(--color-warning);
  color: var(--color-warning);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast) var(--ease-out);
}
.reset:hover {
  background: var(--color-warning);
  color: #ffffff;
}
</style>
