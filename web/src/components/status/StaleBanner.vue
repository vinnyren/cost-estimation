<script setup lang="ts">
defineEmits<{ (e: "recompute"): void }>();
</script>

<template>
  <aside
    class="stale"
    role="status"
    aria-live="polite"
  >
    <span>参数已变，结果可能过期</span>
    <button
      type="button"
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
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  background: var(--color-warn-bg);
  border-left: 3px solid var(--color-warn-stripe);
}
button {
  min-height: 44px;
  padding: 0 var(--space-3);
}
</style>
