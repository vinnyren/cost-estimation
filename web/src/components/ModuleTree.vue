<script setup lang="ts">
import { computed, ref } from "vue";
import type { FunctionPoint } from "@/api/functions";

const props = defineProps<{
  functions: Pick<FunctionPoint, "id" | "subsystem" | "l1_module" | "category" | "us">[];
}>();

// select 事件 payload：null = 全部；否则是某个一级模块
type ModuleSel = { subsystem: string; l1_module: string } | null;
const emit = defineEmits<{
  (e: "select", payload: ModuleSel): void;
}>();

// 选中状态 —— "全部" 或 "subsystem||l1_module"
const selectedKey = ref<string>("__all__");

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

function keyOf(subsystem: string, l1: string): string {
  return `${subsystem}||${l1}`;
}

function selectAll(): void {
  selectedKey.value = "__all__";
  emit("select", null);
}

function selectModule(subsystem: string, l1_module: string): void {
  selectedKey.value = keyOf(subsystem, l1_module);
  emit("select", { subsystem, l1_module });
}
</script>

<template>
  <nav
    class="tree"
    aria-label="模块树"
  >
    <button
      type="button"
      class="all-item"
      :class="{ active: selectedKey === '__all__' }"
      data-test="all"
      @click="selectAll"
    >
      <span class="leaf-name">全部功能点</span>
      <span class="count">{{ functions.length }}</span>
    </button>
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
              :class="{ active: selectedKey === keyOf(sub.subsystem, m.name) }"
              @click="selectModule(sub.subsystem, m.name)"
              @keydown.enter="selectModule(sub.subsystem, m.name)"
              @keydown.space.prevent="selectModule(sub.subsystem, m.name)"
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
/* 窄屏跟随父布局自适应宽度，避免 240px 把表格挤掉 */
@media (max-width: 768px) {
  .tree {
    width: 100%;
    height: auto;
  }
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
.all-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  margin-bottom: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  color: var(--color-text-body);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  min-height: var(--touch-target);
  transition: all var(--duration-fast) var(--ease-out);
}
.all-item:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
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
/* 选中态 —— 比 hover 更实，持续显示当前过滤的模块 */
.leaf.active,
.all-item.active {
  background: var(--color-primary, #165dff);
  color: #fff;
  border-color: var(--color-primary, #165dff);
}
.leaf.active:hover,
.all-item.active:hover {
  background: var(--color-primary, #165dff);
  color: #fff;
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
.leaf.active .count,
.all-item.active .count {
  background: rgba(255, 255, 255, 0.22);
  border-color: transparent;
  color: #fff;
}
</style>
