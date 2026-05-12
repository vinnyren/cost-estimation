<script setup lang="ts">
// v2.0 T21 — Row-level overflow menu for the project list (GAP-I / GAP-J 前端).
// Hosts the three secondary project actions — copy, audit, delete — that don't
// deserve a permanent button on each card. Clicking the trigger toggles a small
// popover; clicking outside closes it (we register the listener on document).
//
// Why this lives in its own component:
//   - keeps ProjectList card markup focused on data, not chrome;
//   - lets us test the menu's open/close + action dispatch in isolation
//     (see web/src/__tests__/ProjectActionMenu.test.ts);
//   - the same control will be reusable on a future ProjectDetail header.
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import { projectsApi } from "@/api/projects";

const props = defineProps<{ projectId: string; projectName: string }>();
const emit = defineEmits<{
  (e: "deleted"): void;
  (e: "copied"): void;
}>();

const open = ref(false);
const router = useRouter();
const root = ref<HTMLElement | null>(null);

function onOutside(ev: MouseEvent): void {
  if (!root.value) return;
  if (!root.value.contains(ev.target as Node)) {
    open.value = false;
  }
}

onMounted(() => document.addEventListener("click", onOutside));
onBeforeUnmount(() => document.removeEventListener("click", onOutside));

async function onCopy(): Promise<void> {
  open.value = false;
  const suggested = `${props.projectName} (副本)`;
  const newName = window.prompt("新项目名", suggested);
  if (!newName || !newName.trim()) return;
  const result = await projectsApi.copy(props.projectId, newName.trim());
  emit("copied");
  router.push(`/projects/${result.id}/functions`);
}

function onEdit(): void {
  open.value = false;
  router.push(`/projects/${props.projectId}/edit`);
}

function onAudit(): void {
  open.value = false;
  router.push(`/projects/${props.projectId}/audit`);
}

async function onDelete(): Promise<void> {
  open.value = false;
  if (!window.confirm(`确定删除「${props.projectName}」？该操作不可恢复。`)) return;
  await projectsApi.remove(props.projectId);
  emit("deleted");
}
</script>

<template>
  <div
    ref="root"
    class="action-menu"
  >
    <button
      type="button"
      class="trigger"
      aria-label="项目操作"
      :aria-expanded="open"
      data-testid="action-menu-trigger"
      @click.stop="open = !open"
    >
      ⋯
    </button>
    <ul
      v-if="open"
      class="menu"
      role="menu"
      data-testid="action-menu"
      @click.stop
    >
      <li
        role="menuitem"
        data-testid="action-menu-edit"
        @click="onEdit"
      >
        ⚙️ 编辑设定
      </li>
      <li
        role="menuitem"
        data-testid="action-menu-copy"
        @click="onCopy"
      >
        📋 复制项目
      </li>
      <li
        role="menuitem"
        data-testid="action-menu-audit"
        @click="onAudit"
      >
        🕒 审计日志
      </li>
      <li
        class="danger"
        role="menuitem"
        data-testid="action-menu-delete"
        @click="onDelete"
      >
        🗑️ 删除
      </li>
    </ul>
  </div>
</template>

<style scoped>
.action-menu {
  position: relative;
  display: inline-block;
}
.trigger {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: var(--space-1) var(--space-3);
  font-size: var(--font-size-lg);
  color: var(--color-text-muted);
  border-radius: var(--radius-md);
}
.trigger:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-body);
}
.menu {
  position: absolute;
  right: 0;
  top: 100%;
  background: var(--color-bg-elevated, #fff);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  list-style: none;
  padding: var(--space-1) 0;
  margin: var(--space-1) 0 0 0;
  min-width: 140px;
  z-index: 10;
  font-size: var(--font-size-sm);
}
.menu li {
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  color: var(--color-text-body);
  white-space: nowrap;
}
.menu li:hover {
  background: var(--color-primary-bg);
  color: var(--color-primary);
}
.menu li.danger {
  color: var(--color-danger);
}
.menu li.danger:hover {
  background: var(--color-danger-bg);
  color: var(--color-danger);
}
</style>
