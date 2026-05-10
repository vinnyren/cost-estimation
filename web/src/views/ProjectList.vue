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
    <header class="header">
      <h1 id="page-title">
        项目列表
      </h1>
      <button
        type="button"
        class="primary"
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
        class="card"
      >
        <header class="card-head">
          <h3>{{ p.name }}</h3>
          <span
            class="mode-badge"
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
            @click="open(p.id)"
          >
            打开
          </button>
          <button
            type="button"
            class="danger"
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
  padding: var(--space-6);
  max-width: 1200px;
  margin: 0 auto;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
}
.primary {
  min-height: 44px;
  padding: 0 var(--space-4);
  background: var(--color-accent);
  color: oklch(100% 0 0);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
}
.primary:hover {
  filter: brightness(1.05);
}
.cards {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
}
.card {
  background: oklch(100% 0 0);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  box-shadow: 0 1px 3px oklch(0% 0 0 / 0.1);
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-head h3 {
  margin: 0;
}
.mode-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: oklch(95% 0.05 250);
  color: var(--color-accent);
}
.mode-badge[data-mode="reverse"] {
  background: oklch(95% 0.06 25);
  color: var(--color-error);
}
.meta {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
  margin: var(--space-3) 0;
  font-size: 14px;
}
.meta dt {
  font-weight: 600;
  color: oklch(40% 0 0);
}
.meta dd {
  margin: 0;
}
.card-actions {
  display: flex;
  gap: var(--space-2);
}
.card-actions button {
  min-height: 44px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-sm);
  border: 1px solid oklch(85% 0 0);
  background: oklch(100% 0 0);
  cursor: pointer;
}
.card-actions button:hover {
  filter: brightness(0.97);
}
.danger {
  color: var(--color-error);
}
</style>
