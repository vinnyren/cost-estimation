<script setup lang="ts">
import { computed } from "vue";
import type { FunctionPoint } from "@/api/functions";

const props = defineProps<{
  functions: Pick<FunctionPoint, "id" | "subsystem" | "l1_module" | "category" | "us">[];
}>();
const emit = defineEmits<{
  (e: "select", payload: { subsystem: string; l1_module: string }): void;
}>();

const tree = computed(() => {
  const map = new Map<string, Map<string, number>>();
  for (const fp of props.functions) {
    const subsystem = fp.subsystem ?? "未分组";
    const l1 = fp.l1_module ?? "未分类";
    if (!map.has(subsystem)) map.set(subsystem, new Map());
    const sub = map.get(subsystem)!;
    sub.set(l1, (sub.get(l1) ?? 0) + 1);
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
    <ul class="tree-root">
      <li
        v-for="sub in tree"
        :key="sub.subsystem"
      >
        <details open>
          <summary>{{ sub.subsystem }}</summary>
          <ul class="tree-leaves">
            <li
              v-for="m in sub.modules"
              :key="m.name"
              data-test="leaf"
              role="button"
              tabindex="0"
              class="leaf"
              @click="emit('select', { subsystem: sub.subsystem, l1_module: m.name })"
              @keydown.enter="emit('select', { subsystem: sub.subsystem, l1_module: m.name })"
              @keydown.space.prevent="emit('select', { subsystem: sub.subsystem, l1_module: m.name })"
            >
              <span class="leaf-name">{{ m.name }}</span>
              <span class="count">{{ m.count }}</span>
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
  width: var(--layout-sidebar-width);
  height: 100%;
  overflow: auto;
  background: var(--color-bg-hover);
  font-size: var(--font-size-sm);
}
.tree-root,
.tree-leaves {
  list-style: none;
  padding: 0;
  margin: 0;
}
.tree-leaves {
  padding-left: var(--space-3);
}
summary {
  font-weight: 600;
  color: var(--color-text-title);
  cursor: pointer;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  min-height: var(--touch-target);
  transition: background var(--duration-fast) var(--ease-out);
}
summary:hover {
  background: var(--color-primary-bg);
  color: var(--color-primary);
}
.leaf {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  min-height: var(--touch-target);
  border-radius: var(--radius-md);
  color: var(--color-text-body);
  transition: all var(--duration-fast) var(--ease-out);
}
.leaf:hover,
.leaf:focus {
  background: var(--color-primary-bg);
  color: var(--color-primary);
  outline: none;
}
.leaf-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.count {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  padding: 0 var(--space-2);
  border-radius: var(--radius-md);
  min-width: 20px;
  text-align: center;
}
.leaf:hover .count,
.leaf:focus .count {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
</style>
