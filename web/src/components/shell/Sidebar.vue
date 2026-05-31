<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import { computed } from "vue";

interface NavItem {
  key: string;
  label: string;
  icon: string;
  to?: string;
  disabled?: boolean;
}

const route = useRoute();
const router = useRouter();

const MAIN_NAV: NavItem[] = [
  { key: "projects", label: "项目工作台", icon: "folder", to: "/" },
  { key: "params-global", label: "全局参数库", icon: "settings", to: "/params/global" },
  { key: "templates", label: "模板与场景", icon: "layers", disabled: true },
  { key: "reports", label: "报告中心", icon: "file", to: "/reports" },
  { key: "audit-global", label: "审计日志", icon: "history", to: "/audit" },
];

const projectId = computed<string | null>(() => {
  const id = route.params.id;
  return typeof id === "string" && id ? id : null;
});

const PROJECT_NAV = computed<NavItem[]>(() => {
  if (!projectId.value) return [];
  return [
    { key: "fp", label: "FP 编辑", icon: "grid", to: `/projects/${projectId.value}/functions` },
    { key: "result", label: "三档造价", icon: "trending", to: `/projects/${projectId.value}/result` },
    { key: "params", label: "参数管理", icon: "settings", to: `/projects/${projectId.value}/parameters` },
    { key: "audit", label: "审计", icon: "history", to: `/projects/${projectId.value}/audit` },
  ];
});

function isActive(item: NavItem): boolean {
  if (!item.to) return false;
  if (item.to === "/") return route.path === "/";
  return route.path.startsWith(item.to);
}

function go(item: NavItem) {
  if (item.disabled || !item.to) return;
  router.push(item.to);
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-brand">
      <div class="sidebar-brand-mark">F</div>
      <div class="sidebar-brand-text">
        <div class="sidebar-brand-title">FP-Studio</div>
        <div class="sidebar-brand-sub mono">v2.9.0 · SSM-BK-202509</div>
      </div>
    </div>

    <nav class="sidebar-nav">
      <div class="sidebar-section-label">主导航</div>
      <a
        v-for="it in MAIN_NAV"
        :key="it.key"
        class="nav-item"
        :class="{ active: isActive(it), disabled: it.disabled }"
        @click="go(it)"
      >
        <span class="nav-icon" :data-icon="it.icon" />
        <span class="nav-label">{{ it.label }}</span>
        <span v-if="it.disabled" class="nav-soon">敬请期待</span>
      </a>

      <template v-if="projectId">
        <div class="sidebar-section-label">当前项目</div>
        <a
          v-for="it in PROJECT_NAV"
          :key="it.key"
          class="nav-item sub"
          :class="{ active: isActive(it) }"
          @click="go(it)"
        >
          <span class="nav-icon" :data-icon="it.icon" />
          <span class="nav-label">{{ it.label }}</span>
        </a>
      </template>
    </nav>

    <div class="sidebar-foot">
      <div class="sidebar-help mono">SSM-BK-202509</div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  background: var(--sidebar-bg);
  color: var(--sidebar-text);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100vh;
}
.sidebar-brand {
  display: flex; align-items: center; gap: 10px;
  padding: 16px 18px 14px;
  border-bottom: 1px solid var(--sidebar-border);
}
.sidebar-brand-mark {
  width: 28px; height: 28px; border-radius: 7px;
  background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%);
  display: grid; place-items: center;
  color: white; font-weight: 700; font-family: var(--font-mono);
  font-size: 13px; letter-spacing: -0.5px;
}
.sidebar-brand-title { color: #fff; font-weight: 600; font-size: 13px; }
.sidebar-brand-sub { color: var(--sidebar-text-muted); font-size: 11px; }
.sidebar-nav { padding: 12px 8px; flex: 1; overflow-y: auto; }
.sidebar-section-label {
  color: var(--sidebar-text-muted);
  font-size: 10px; font-weight: 600;
  letter-spacing: 0.08em; text-transform: uppercase;
  padding: 12px 10px 4px;
}
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 7px 10px; border-radius: var(--radius);
  color: var(--sidebar-text); cursor: pointer;
  font-size: 13px; transition: background var(--duration-fast);
}
.nav-item:hover { background: rgba(255, 255, 255, 0.04); }
.nav-item.active {
  background: var(--sidebar-active-bg);
  color: var(--sidebar-active-text);
  box-shadow: inset 2px 0 0 var(--accent);
}
.nav-item.disabled { color: var(--sidebar-text-muted); cursor: not-allowed; }
.nav-item.sub { padding-left: 22px; }
.nav-icon {
  width: 14px; height: 14px;
  background: currentColor;
  mask: var(--icon-url) center/contain no-repeat;
  flex-shrink: 0;
}
.nav-label { flex: 1; }
.nav-soon {
  font-size: 10px; padding: 1px 6px;
  background: rgba(255, 255, 255, 0.06); border-radius: 3px;
  color: var(--sidebar-text-muted);
}
.sidebar-foot { padding: 12px 18px; border-top: 1px solid var(--sidebar-border); }
.sidebar-help { color: var(--sidebar-text-muted); font-size: 10px; }
</style>
