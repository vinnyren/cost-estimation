<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import Breadcrumbs from "./Breadcrumbs.vue";

const router = useRouter();
const paletteOpen = ref(false);

function openPalette() { paletteOpen.value = true; }
function gotoAudit() { router.push("/audit"); }

defineExpose({ openPalette });
</script>

<template>
  <div class="topbar-root">
    <header class="topbar">
      <Breadcrumbs />
      <div class="topbar-spacer" />
      <button class="topbar-search" @click="openPalette" aria-label="打开命令面板 (⌘K)">
        <span class="topbar-search-icon">🔍</span>
        <span class="topbar-search-text">搜索项目、城市、模块… (⌘K)</span>
      </button>
      <button class="icon-btn" title="审计日志" @click="gotoAudit">📜</button>
      <button class="icon-btn" title="帮助">？</button>
      <div class="user-chip">
        <div class="user-avatar">用</div>
        <div class="user-meta">
          <div>当前用户</div>
          <div class="muted">咨询编辑</div>
        </div>
      </div>
    </header>
    <!-- CommandPalette 留 T6 集成 -->
  </div>
</template>

<style scoped>
.topbar-root { display: contents; }
.topbar {
  height: var(--layout-topbar-height);
  padding: 0 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 12px;
  flex-shrink: 0;
}
.topbar-spacer { flex: 1; }
.topbar-search {
  display: inline-flex; align-items: center; gap: 8px;
  height: 32px; padding: 0 12px; min-width: 320px;
  background: var(--surface-2); border: 1px solid var(--border);
  border-radius: var(--radius); color: var(--text-3); font-size: 12px;
}
.topbar-search:hover { border-color: var(--accent); }
.user-chip {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 4px 10px 4px 4px;
  border-radius: 18px; border: 1px solid var(--border);
  background: var(--surface-2); font-size: 12px;
}
.user-avatar {
  width: 26px; height: 26px; border-radius: 50%;
  background: var(--accent); color: #fff;
  display: grid; place-items: center; font-weight: 600;
}
.user-meta { line-height: 1.2; }
.user-meta .muted { font-size: 10px; }
</style>
