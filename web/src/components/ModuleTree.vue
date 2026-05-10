<script setup lang="ts">
import { computed } from "vue";
import type { FunctionPoint } from "@/api/functions";

const props = defineProps<{
  functions: Pick<FunctionPoint, "id" | "subsystem" | "module_l1" | "category" | "us">[];
}>();
const emit = defineEmits<{
  (e: "select", payload: { subsystem: string; module_l1: string }): void;
}>();

const tree = computed(() => {
  const map = new Map<string, Map<string, number>>();
  for (const fp of props.functions) {
    if (!map.has(fp.subsystem)) map.set(fp.subsystem, new Map());
    const sub = map.get(fp.subsystem)!;
    sub.set(fp.module_l1, (sub.get(fp.module_l1) ?? 0) + 1);
  }
  return Array.from(map.entries()).map(([sub, mods]) => ({
    subsystem: sub,
    modules: Array.from(mods.entries()).map(([m, count]) => ({ name: m, count })),
  }));
});
</script>

<template>
  <nav
    class="tree"
    aria-label="模块树"
  >
    <ul>
      <li
        v-for="sub in tree"
        :key="sub.subsystem"
      >
        <details open>
          <summary>{{ sub.subsystem }}</summary>
          <ul>
            <li
              v-for="m in sub.modules"
              :key="m.name"
              data-test="leaf"
              role="button"
              tabindex="0"
              @click="emit('select', { subsystem: sub.subsystem, module_l1: m.name })"
              @keydown.enter="emit('select', { subsystem: sub.subsystem, module_l1: m.name })"
              @keydown.space.prevent="emit('select', { subsystem: sub.subsystem, module_l1: m.name })"
            >
              {{ m.name }} <span class="count">({{ m.count }})</span>
            </li>
          </ul>
        </details>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.tree {
  padding: var(--space-3);
  width: 240px;
  border-right: 1px solid oklch(90% 0 0);
  height: 100%;
  overflow: auto;
}
ul {
  list-style: none;
  padding: 0 0 0 var(--space-3);
  margin: 0;
}
li {
  padding: var(--space-1) 0;
  cursor: pointer;
  min-height: 44px;
  display: flex;
  align-items: center;
}
li:hover,
li:focus {
  background: oklch(95% 0.05 250);
  outline: none;
}
.count {
  color: oklch(50% 0 0);
  font-size: 12px;
  margin-left: var(--space-1);
}
summary {
  font-weight: 600;
  cursor: pointer;
  padding: var(--space-1) 0;
  min-height: 44px;
  display: flex;
  align-items: center;
}
</style>
