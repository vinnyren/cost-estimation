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
    <div
      class="icon"
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 24 24"
        width="20"
        height="20"
      >
        <circle
          cx="12"
          cy="12"
          r="10"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        />
        <path
          d="M12 7 v6 M12 16 v0.5"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        />
      </svg>
    </div>
    <div class="content">
      <strong class="problem">{{ problem }}</strong>
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
      class="btn btn-sm retry-btn"
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
  padding: var(--space-3) var(--space-4);
  background: var(--color-danger-bg);
  border: 1px solid var(--color-danger);
  border-left-width: 4px;
  border-radius: var(--radius-md);
  align-items: flex-start;
}
.icon {
  color: var(--color-danger);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  margin-top: 2px;
}
.content {
  flex: 1;
  min-width: 0;
}
.problem {
  color: var(--color-text-title);
  font-weight: 600;
  display: block;
  margin-bottom: var(--space-1);
}
.cause,
.suggestion {
  margin: var(--space-1) 0 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-body);
}
.retry-btn {
  flex-shrink: 0;
  align-self: flex-start;
  background: var(--color-bg-elevated);
}
.retry-btn:hover {
  background: var(--color-danger);
  border-color: var(--color-danger);
  color: #ffffff;
}
</style>
