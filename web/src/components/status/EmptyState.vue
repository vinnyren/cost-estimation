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
    <h2>{{ title }}</h2>
    <p v-if="description">
      {{ description }}
    </p>
    <button
      v-if="ctaLabel"
      type="button"
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
  padding: var(--space-8);
  gap: var(--space-3);
}
button {
  min-height: 44px;
  min-width: 120px;
  background: var(--color-accent);
  color: oklch(100% 0 0);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
}
button:hover {
  filter: brightness(1.05);
}
</style>
