<script setup lang="ts">
// v2.2 T28 — AuditView：表格 → timeline，复用 AuditTimeline 组件。
// v2.7 — global 分支补全：调 auditApi.listGlobal 渲染跨项目聚合时间线。
import { ref, onMounted, computed } from "vue";
import { useRoute } from "vue-router";
import {
  auditApi,
  type AuditEntry,
  type GlobalAuditEntry,
} from "@/api/audit";
import AuditTimeline from "@/components/audit/AuditTimeline.vue";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";

const props = defineProps<{ global?: boolean }>();

const PAGE_SIZE = 50;

const route = useRoute();
const projectId = computed(() => {
  const id = route.params.id;
  return typeof id === "string" && id ? id : null;
});
const entries = ref<Array<AuditEntry | GlobalAuditEntry>>([]);
const loading = ref(false);
const hasMore = ref(true);

async function reload(beforeId?: number): Promise<void> {
  loading.value = true;
  try {
    let more: Array<AuditEntry | GlobalAuditEntry>;
    if (props.global) {
      more = await auditApi.listGlobal({ limit: PAGE_SIZE, beforeId });
    } else {
      if (!projectId.value) return;
      more = await auditApi.list(projectId.value, { limit: PAGE_SIZE, beforeId });
    }
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
  if (props.global || projectId.value) void reload();
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
          <template v-if="global">{{ entries.length }} 条事件 · 跨项目聚合 · keyset 分页</template>
          <template v-else>{{ entries.length }} 条事件 · 不可变 append-only · keyset 分页</template>
        </div>
      </div>
    </div>

    <LoadingSkeleton v-if="loading && entries.length === 0" />
    <div
      v-else-if="entries.length === 0"
      class="card"
      style="padding: 40px; text-align: center; color: var(--text-3)"
    >
      暂无审计事件
    </div>
    <div v-else class="card" style="padding: 20px 24px">
      <AuditTimeline :events="entries" :show-project="global" />
      <div v-if="hasMore" style="margin-top: 20px; text-align: center">
        <button class="btn btn-ghost btn-sm" :disabled="loading" @click="onLoadMore">
          {{ loading ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </div>
  </div>
</template>
