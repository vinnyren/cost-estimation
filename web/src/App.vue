<script setup lang="ts">
</script>

<template>
  <div class="app-shell">
    <header
      class="app-header"
      role="banner"
    >
      <h1 class="app-logo">
        软件造价制作系统
      </h1>
      <span class="app-meta text-muted">v1.0 · CSBMK®-202510</span>
    </header>
    <main
      class="app-main"
      aria-live="polite"
    >
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.app-header {
  height: var(--layout-header-height);
  padding: 0 var(--space-6);
  background: var(--color-bg-elevated);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
}
.app-logo {
  margin: 0;
  font-size: var(--font-size-md);
  color: var(--color-text-title);
  font-weight: 600;
  line-height: 1.2;
}
.app-meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
.app-main {
  flex: 1;
  padding: var(--space-6);
  max-width: var(--layout-max-width);
  margin: 0 auto;
  width: 100%;
}
</style>
