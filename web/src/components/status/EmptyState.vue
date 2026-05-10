<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
  ctaLabel?: string;
}>();
defineEmits<{ (e: "cta-click"): void }>();
</script>

<template>
  <section class="empty">
    <div class="empty-illustration">
      <svg
        viewBox="0 0 64 64"
        width="48"
        height="48"
        aria-hidden="true"
      >
        <circle
          cx="32"
          cy="32"
          r="28"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-dasharray="4 4"
          opacity="0.4"
        />
        <path
          d="M22 30 h20 M22 38 h14"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          opacity="0.6"
        />
      </svg>
    </div>
    <h2>{{ title }}</h2>
    <p
      v-if="description"
      class="desc"
    >
      {{ description }}
    </p>
    <button
      v-if="ctaLabel"
      type="button"
      class="btn btn-primary"
      @click="$emit('cta-click')"
    >
      {{ ctaLabel }}
    </button>
  </section>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-10) var(--space-6);
  gap: var(--space-3);
  background: var(--color-bg-elevated);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-lg);
  text-align: center;
}
.empty-illustration {
  color: var(--color-text-muted);
  margin-bottom: var(--space-2);
}
.empty h2 {
  margin: 0;
  font-size: var(--font-size-md);
  color: var(--color-text-title);
}
.desc {
  margin: 0 0 var(--space-2) 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}
</style>
