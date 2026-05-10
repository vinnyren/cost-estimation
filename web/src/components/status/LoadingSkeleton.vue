<script setup lang="ts">
defineProps<{ rows?: number }>();
</script>

<template>
  <div
    role="status"
    aria-live="polite"
    aria-busy="true"
    class="skeleton-wrap"
  >
    <div
      v-for="i in rows ?? 3"
      :key="i"
      data-test="skeleton-row"
      class="skeleton-row"
    />
    <span class="visually-hidden">加载中</span>
  </div>
</template>

<style scoped>
.skeleton-wrap {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.skeleton-row {
  height: 32px;
  border-radius: var(--radius-sm);
  background: linear-gradient(
    90deg,
    oklch(94% 0 0),
    oklch(97% 0 0),
    oklch(94% 0 0)
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}
@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
