<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import { computed } from "vue";
import { useProjectsStore } from "@/stores/projects";

const route = useRoute();
const router = useRouter();
const projectsStore = useProjectsStore();

interface Crumb { label: string; to?: string; }

const crumbs = computed<Crumb[]>(() => {
  const out: Crumb[] = [{ label: "项目工作台", to: "/" }];
  const id = typeof route.params.id === "string" ? route.params.id : null;

  if (route.name === "project-wizard") out.push({ label: "新建项目" });
  if (id) {
    const project = projectsStore.items.find((p: { id: string }) => p.id === id);
    out.push({ label: project?.name ?? id, to: `/projects/${id}/functions` });
    if (route.name === "param-manager") out.push({ label: "参数管理" });
    if (route.name === "result-view") out.push({ label: "三档造价" });
    if (route.name === "project-audit") out.push({ label: "审计" });
  }
  if (route.name === "audit-global") out[0] = { label: "审计日志" };
  if (route.name === "params-global") out[0] = { label: "全局参数库" };
  if (route.name === "report-center") out[0] = { label: "报告中心" };
  return out;
});

function jump(to: string | undefined) { if (to) router.push(to); }
</script>

<template>
  <nav class="crumbs" aria-label="面包屑">
    <template v-for="(c, i) in crumbs" :key="i">
      <span v-if="i > 0" class="crumb-sep" aria-hidden="true">›</span>
      <a class="crumb" :class="{ current: i === crumbs.length - 1 }" @click="jump(c.to)">
        {{ c.label }}
      </a>
    </template>
  </nav>
</template>

<style scoped>
.crumbs { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.crumb { color: var(--text-3); cursor: pointer; }
.crumb:hover { color: var(--accent); }
.crumb.current { color: var(--text); font-weight: 500; cursor: default; }
.crumb-sep { color: var(--text-4); font-size: 11px; }
</style>
