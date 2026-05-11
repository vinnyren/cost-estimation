<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from "vue";
import Sidebar from "@/components/shell/Sidebar.vue";
import Topbar from "@/components/shell/Topbar.vue";

const topbarRef = ref<InstanceType<typeof Topbar> | null>(null);

function onKey(e: KeyboardEvent) {
  const isMod = e.metaKey || e.ctrlKey;
  if (isMod && e.key.toLowerCase() === "k") {
    e.preventDefault();
    topbarRef.value?.openPalette();
  }
}

onMounted(() => window.addEventListener("keydown", onKey));
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
</script>

<template>
  <div class="app">
    <Sidebar />
    <div class="app-main">
      <Topbar ref="topbarRef" />
      <main class="app-content" aria-live="polite">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  min-height: 100vh;
}

.app-main {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.app-content {
  flex: 1;
  padding: var(--space-6);
  max-width: var(--layout-max-width);
  margin: 0 auto;
  width: 100%;
}
</style>
