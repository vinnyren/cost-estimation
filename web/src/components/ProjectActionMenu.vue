<script setup lang="ts">
// v2.0 T21 — Row-level overflow menu for the project list (GAP-I / GAP-J 前端).
// Hosts the three secondary project actions — copy, audit, delete — that don't
// deserve a permanent button on each card. Clicking the trigger toggles a small
// popover; clicking outside closes it (we register the listener on document).
//
// v2.5 fix: 下拉用 <Teleport to="body"> + fixed 定位，避免被项目列表表格的
// overflow 容器裁剪。位置按 trigger 的 getBoundingClientRect 计算，右对齐；
// 下方空间不足时翻到上方。
import { ref, onMounted, onBeforeUnmount, nextTick } from "vue";
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
const menuEl = ref<HTMLElement | null>(null);
const menuStyle = ref<Record<string, string>>({});

const MENU_WIDTH = 150;
const MENU_HEIGHT = 184; // 4 项 ≈ 184px，用于翻转判断
const VIEWPORT_MARGIN = 8;

function positionMenu(): void {
  const trigger = root.value?.querySelector(".trigger") as HTMLElement | null;
  if (!trigger) return;
  const r = trigger.getBoundingClientRect();
  // 右对齐 trigger 右边缘
  let left = r.right - MENU_WIDTH;
  if (left < VIEWPORT_MARGIN) left = VIEWPORT_MARGIN;
  // 默认在 trigger 下方；下方空间不足则翻到上方
  let top = r.bottom + 4;
  if (top + MENU_HEIGHT > window.innerHeight - VIEWPORT_MARGIN) {
    top = Math.max(VIEWPORT_MARGIN, r.top - MENU_HEIGHT - 4);
  }
  menuStyle.value = {
    position: "fixed",
    top: `${top}px`,
    left: `${left}px`,
  };
}

async function toggle(): Promise<void> {
  open.value = !open.value;
  if (open.value) {
    await nextTick();
    positionMenu();
  }
}

function onOutside(ev: MouseEvent): void {
  const target = ev.target as Node;
  if (root.value?.contains(target)) return;
  if (menuEl.value?.contains(target)) return;
  open.value = false;
}

// fixed 定位的菜单不跟随滚动 — 滚动时直接关闭，避免菜单与行错位
function onScroll(): void {
  if (open.value) open.value = false;
}

onMounted(() => {
  document.addEventListener("click", onOutside);
  window.addEventListener("scroll", onScroll, true);
});
onBeforeUnmount(() => {
  document.removeEventListener("click", onOutside);
  window.removeEventListener("scroll", onScroll, true);
});

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
      @click.stop="toggle"
    >
      ⋯
    </button>
    <Teleport to="body">
      <ul
        v-if="open"
        ref="menuEl"
        class="menu"
        role="menu"
        data-testid="action-menu"
        :style="menuStyle"
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
    </Teleport>
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
</style>

<style>
/* 非 scoped — 菜单 Teleport 到 body，scoped 的 [data-v] 属性选择器够不到。 */
.action-menu-menu-reset,
ul.menu[data-testid="action-menu"] {
  position: fixed;
  background: var(--color-bg-elevated, #fff);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: var(--radius-md, 8px);
  box-shadow: var(--shadow-md, 0 4px 16px rgba(15, 23, 42, 0.16));
  list-style: none;
  padding: var(--space-1, 4px) 0;
  margin: 0;
  min-width: 150px;
  z-index: 2000;
  font-size: var(--font-size-sm, 13px);
}
ul.menu[data-testid="action-menu"] li {
  padding: var(--space-2, 8px) var(--space-3, 12px);
  cursor: pointer;
  color: var(--color-text-body, #1e293b);
  white-space: nowrap;
}
ul.menu[data-testid="action-menu"] li:hover {
  background: var(--color-primary-bg, #eef3ff);
  color: var(--color-primary, #165dff);
}
ul.menu[data-testid="action-menu"] li.danger {
  color: var(--color-danger, #dc2626);
}
ul.menu[data-testid="action-menu"] li.danger:hover {
  background: var(--color-danger-bg, #fef2f2);
  color: var(--color-danger, #dc2626);
}
</style>
