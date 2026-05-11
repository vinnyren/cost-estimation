<script setup lang="ts">
// v2.2 T28 — AuditView 重做：表格 → timeline，复用 AuditTimeline 组件。
// 接受 global prop 用于 /audit 全局路由 (server 暂无全局 endpoint，placeholder)。
import { ref, onMounted, computed } from "vue";
import { useRoute } from "vue-router";
import { auditApi, type AuditEntry } from "@/api/audit";
import AuditTimeline from "@/components/audit/AuditTimeline.vue";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";

const props = defineProps<{ global?: boolean }>();

const PAGE_SIZE = 50;

const route = useRoute();
const projectId = computed(() => {
  const id = route.params.id;
  return typeof id === "string" && id ? id : null;
});
const entries = ref<AuditEntry[]>([]);
const loading = ref(false);
const hasMore = ref(true);

async function reload(beforeId?: number): Promise<void> {
  if (props.global || !projectId.value) return;
  loading.value = true;
  try {
    const more = await auditApi.list(projectId.value, { limit: PAGE_SIZE, beforeId });
    if (beforeId !== undefined) {
      entries.value = [...entries.value, ...more];
    } else {
      entries.value = more;
    }
    if (more.length < PAGE_SIZE) hasMore.value = false;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  if (!props.global) void reload();
});

async function onLoadMore(): Promise<void> {
  const last = entries.value[entries.value.length - 1];
  if (last) await reload(last.id);
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title tight">
          {{ global ? '全局审计日志' : '项目审计' }}
        </h1>
        <div class="page-sub">
          <template v-if="!global">{{ entries.length }} 条事件 · 不可变 append-only · keyset 分页</template>
          <template v-else>全局审计聚合视图 · v2.3 实装</template>
        </div>
      </div>
    </div>

    <div v-if="global" class="card" style="padding: 40px; text-align: center; color: var(--text-3)">
      全局审计聚合视图（跨项目）将在 v2.3 上线。
      请通过 <strong>侧边栏 → 项目工作台</strong> 选择具体项目查看其审计时间线。
    </div>

    <template v-else>
      <LoadingSkeleton v-if="loading && entries.length === 0" />
      <div v-else-if="entries.length === 0" class="card" style="padding: 40px; text-align: center; color: var(--text-3)">
        暂无审计事件
      </div>
      <div v-else class="card" style="padding: 20px 24px">
        <AuditTimeline :events="entries" />
        <div v-if="hasMore" style="margin-top: 20px; text-align: center">
          <button class="btn btn-ghost btn-sm" :disabled="loading" @click="onLoadMore">
            {{ loading ? '加载中...' : '加载更多' }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>
