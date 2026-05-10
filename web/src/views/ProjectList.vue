<script setup lang="ts">
import { onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { useProjectsStore } from "@/stores/projects";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import EmptyState from "@/components/status/EmptyState.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";

const COST_PER_WAN = 10000;
const COST_DECIMALS = 2;

const router = useRouter();
const store = useProjectsStore();

const isLoading = computed(() => store.state === "loading" || store.state === "idle");
const isEmpty = computed(() => store.state === "success" && store.items.length === 0);
const isError = computed(() => store.state === "error");
const hasItems = computed(() => store.state === "success" && store.items.length > 0);

onMounted(() => store.fetchAll());

function goNew(): void {
  router.push({ name: "project-wizard" });
}

function open(id: string): void {
  router.push({ name: "fp-editor", params: { id } });
}

async function remove(id: string): Promise<void> {
  if (!window.confirm("确认删除项目？")) return;
  await store.remove(id);
}

function formatCost(value: number): string {
  return (value / COST_PER_WAN).toFixed(COST_DECIMALS);
}
</script>

<template>
  <section
    class="page"
    aria-labelledby="page-title"
  >
    <header class="page-header">
      <h1 id="page-title">
        项目列表
      </h1>
      <button
        type="button"
        class="btn btn-primary"
        @click="goNew"
      >
        新建项目
      </button>
    </header>

    <LoadingSkeleton
      v-if="isLoading"
      :rows="3"
    />

    <ErrorBanner
      v-else-if="isError"
      :problem="'无法加载项目列表'"
      :cause="store.error?.message ?? '未知错误'"
      :suggestion="'请检查后端服务是否启动后重试'"
      :retryable="true"
      @retry="store.fetchAll"
    />

    <EmptyState
      v-else-if="isEmpty"
      :title="'还没有项目'"
      :description="'创建你的第一个造价评估项目'"
      :cta-label="'新建第一个项目'"
      @cta-click="goNew"
    />

    <ul
      v-else-if="hasItems"
      class="cards"
      aria-label="项目列表"
    >
      <li
        v-for="p in store.items"
        :key="p.id"
        class="card project-card"
      >
        <header class="card-head">
          <h3>{{ p.name }}</h3>
          <span
            class="badge"
            :class="p.mode === 'forward' ? 'badge-primary' : 'badge-data'"
            :data-mode="p.mode"
          >{{ p.mode === "forward" ? "正向" : "反向" }}</span>
        </header>
        <dl class="meta">
          <div>
            <dt>城市</dt>
            <dd>{{ p.city }}</dd>
          </div>
          <div>
            <dt>行业</dt>
            <dd>{{ p.industry }}</dd>
          </div>
          <div>
            <dt>阶段</dt>
            <dd>{{ p.phase }}</dd>
          </div>
          <div v-if="p.total_fp !== undefined">
            <dt>FP</dt>
            <dd>{{ p.total_fp }}</dd>
          </div>
          <div v-if="p.total_cost !== undefined">
            <dt>费用</dt>
            <dd>{{ formatCost(p.total_cost) }} 万元</dd>
          </div>
        </dl>
        <footer class="card-actions">
          <button
            type="button"
            class="btn btn-sm"
            @click="open(p.id)"
          >
            打开
          </button>
          <button
            type="button"
            class="btn btn-sm btn-danger"
            @click="remove(p.id)"
          >
            删除
          </button>
        </footer>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.page-header h1 {
  margin: 0;
}
.cards {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-4);
}
.project-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
}
.card-head h3 {
  margin: 0;
  font-size: var(--font-size-md);
  color: var(--color-text-title);
}
.meta {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2) var(--space-4);
  margin: 0;
  font-size: var(--font-size-sm);
}
.meta > div {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}
.meta dt {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: 500;
  min-width: 32px;
}
.meta dd {
  margin: 0;
  color: var(--color-text-body);
}
.card-actions {
  display: flex;
  gap: var(--space-2);
  margin-top: auto;
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}
</style>
