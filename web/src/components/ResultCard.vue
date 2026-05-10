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
    class="result-card"
    :data-band="band"
  >
    <header class="head">
      <span class="band">{{ band }}</span>
      <span class="band-label">{{ bandLabel }}</span>
      <span
        v-if="recommended"
        class="badge badge-primary recommend-badge"
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
.result-card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  transition: box-shadow var(--duration-fast) var(--ease-out),
              transform var(--duration-fast) var(--ease-out);
}
.result-card:hover {
  box-shadow: var(--shadow-md);
}
.result-card[data-recommended="true"] {
  border: 2px solid var(--color-primary);
  background: var(--color-primary-bg);
  box-shadow: var(--shadow-md);
}
.head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.band {
  font-weight: 700;
  color: var(--color-text-title);
  font-size: var(--font-size-md);
  letter-spacing: 0.02em;
}
.result-card[data-recommended="true"] .band {
  color: var(--color-primary);
}
.band-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
.recommend-badge {
  margin-left: auto;
}
.value {
  margin: var(--space-2) 0 0 0;
  display: flex;
  align-items: baseline;
  gap: var(--space-1);
  color: var(--color-text-title);
}
.value strong {
  font-size: 32px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--color-text-title);
}
.result-card[data-recommended="true"] .value strong {
  color: var(--color-primary);
}
.suffix {
  font-size: var(--font-size-md);
  color: var(--color-text-muted);
  font-weight: 500;
}
.desc {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  margin: 0;
  line-height: var(--line-height-base);
}
</style>
