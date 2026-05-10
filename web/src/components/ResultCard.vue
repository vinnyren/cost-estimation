<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  band: "P10" | "P50" | "P90";
  value: number;
  unit: "元" | "FP" | "人月";
  recommended?: boolean;
  description?: string;
}>();

const display = computed(() => {
  if (props.unit === "元") {
    return { num: (props.value / 10000).toFixed(2), suffix: "万元" };
  }
  if (props.unit === "FP") {
    return { num: props.value.toFixed(1), suffix: "FP" };
  }
  return { num: props.value.toFixed(1), suffix: "人月" };
});

const bandLabel = computed(() => {
  if (props.band === "P10") return "乐观";
  if (props.band === "P50") return "中位";
  return "保守";
});
</script>

<template>
  <article
    :data-recommended="recommended"
    class="card"
    :data-band="band"
  >
    <header>
      <span class="band">{{ band }}</span>
      <span class="band-label">{{ bandLabel }}</span>
      <span
        v-if="recommended"
        class="badge"
      >推荐</span>
    </header>
    <p class="value">
      <strong>{{ display.num }}</strong>
      <span class="suffix">{{ display.suffix }}</span>
    </p>
    <p
      v-if="description"
      class="desc"
    >
      {{ description }}
    </p>
  </article>
</template>

<style scoped>
.card {
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: white;
  box-shadow: 0 1px 3px oklch(0% 0 0 / 0.08);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  transition: transform var(--duration-fast) var(--ease-out);
}
.card[data-recommended="true"] {
  border: 2px solid var(--color-accent);
  transform: scale(1.05);
}
header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.band {
  font-weight: 700;
  color: var(--color-accent);
}
.band-label {
  font-size: 14px;
  color: oklch(50% 0 0);
}
.badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--color-accent);
  color: white;
}
.value {
  font-size: 24px;
  margin: 0;
}
.value strong {
  font-size: 32px;
}
.suffix {
  font-size: 16px;
  color: oklch(50% 0 0);
  margin-left: 4px;
}
.desc {
  color: oklch(50% 0 0);
  font-size: 14px;
  margin: 0;
}
</style>
