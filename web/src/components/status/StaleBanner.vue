<script setup lang="ts">
defineEmits<{ (e: "recompute"): void }>();
</script>

<template>
  <aside
    class="stale"
    role="status"
    aria-live="polite"
  >
    <span
      class="icon"
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 24 24"
        width="18"
        height="18"
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
          d="M12 7 v5 l3 2"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          fill="none"
        />
      </svg>
    </span>
    <span class="msg">参数已变，结果可能过期</span>
    <button
      type="button"
      class="btn btn-sm recompute-btn"
      @click="$emit('recompute')"
    >
      重新计算
    </button>
  </aside>
</template>

<style scoped>
.stale {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3) var(--space-2) var(--space-2);
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning);
  border-left-width: 4px;
  border-radius: var(--radius-md);
}
.icon {
  color: var(--color-warning);
  display: flex;
  align-items: center;
}
.msg {
  flex: 1;
  color: var(--color-text-body);
  font-size: var(--font-size-sm);
}
.recompute-btn {
  background: var(--color-bg-elevated);
  border-color: var(--color-warning);
  color: var(--color-warning);
}
.recompute-btn:hover {
  background: var(--color-warning);
  border-color: var(--color-warning);
  color: #ffffff;
}
</style>
