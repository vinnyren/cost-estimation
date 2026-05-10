<script setup lang="ts">
defineProps<{
  problem: string;
  cause: string;
  suggestion: string;
  retryable?: boolean;
}>();
defineEmits<{ (e: "retry"): void }>();
</script>

<template>
  <aside
    role="alert"
    class="error-banner"
  >
    <div class="content">
      <strong>{{ problem }}</strong>
      <p class="cause">
        原因：{{ cause }}
      </p>
      <p class="suggestion">
        建议：{{ suggestion }}
      </p>
    </div>
    <button
      v-if="retryable"
      type="button"
      data-test="retry"
      @click="$emit('retry')"
    >
      重试
    </button>
  </aside>
</template>

<style scoped>
.error-banner {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3);
  background: oklch(96% 0.06 25);
  border-left: 4px solid var(--color-error);
  border-radius: var(--radius-sm);
  align-items: flex-start;
}
.content {
  flex: 1;
}
.cause,
.suggestion {
  margin: var(--space-1) 0 0 0;
  font-size: 14px;
}
button {
  min-height: 44px;
  padding: 0 var(--space-3);
}
</style>
