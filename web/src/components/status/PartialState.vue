<script setup lang="ts">
defineProps<{ doneCount: number; totalCount: number; cancellable?: boolean }>();
defineEmits<{ (e: "cancel"): void }>();
</script>

<template>
  <div
    role="status"
    aria-live="polite"
    class="partial"
  >
    <progress
      :value="doneCount"
      :max="totalCount"
    />
    <span class="count">{{ doneCount }} / {{ totalCount }}</span>
    <button
      v-if="cancellable"
      type="button"
      class="btn btn-sm"
      @click="$emit('cancel')"
    >
      取消
    </button>
  </div>
</template>

<style scoped>
.partial {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}
progress {
  flex: 1;
  height: 6px;
  border: none;
  border-radius: var(--radius-sm);
  overflow: hidden;
  appearance: none;
  background: var(--color-bg);
}
progress::-webkit-progress-bar {
  background: var(--color-bg);
  border-radius: var(--radius-sm);
}
progress::-webkit-progress-value {
  background: var(--color-primary);
  border-radius: var(--radius-sm);
  transition: width var(--duration-normal) var(--ease-out);
}
progress::-moz-progress-bar {
  background: var(--color-primary);
  border-radius: var(--radius-sm);
}
.count {
  font-size: var(--font-size-sm);
  color: var(--color-text-body);
  font-variant-numeric: tabular-nums;
  min-width: 60px;
  text-align: right;
}
</style>
