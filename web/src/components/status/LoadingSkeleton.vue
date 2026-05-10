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
  position: relative;
  overflow: hidden;
  height: 32px;
  border-radius: var(--radius-md);
  background: var(--color-border);
}
.skeleton-row::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.6),
    transparent
  );
  transform: translateX(-100%);
  animation: shimmer 1.5s ease-in-out infinite;
  will-change: transform;
}
@keyframes shimmer {
  100% {
    transform: translateX(100%);
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
