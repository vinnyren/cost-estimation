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
    <span>{{ doneCount }} / {{ totalCount }}</span>
    <button
      v-if="cancellable"
      type="button"
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
  padding: var(--space-2);
}
progress {
  flex: 1;
}
button {
  min-height: 44px;
  padding: 0 var(--space-3);
}
</style>
