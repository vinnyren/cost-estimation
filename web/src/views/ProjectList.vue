<script setup lang="ts">
/**
 * ProjectList — 项目列表页（v2.0 加 toolbar + ⋯ 行操作）。
 *
 * v1.1 只有简单列表 + 新建按钮；v2.0 新增：
 *   - toolbar：搜索（防抖 250ms）+ 城市/行业/阶段筛选 + 排序字段 + 升降序
 *   - 分页（PAGE_SIZE=20，total/meta 由 query envelope 提供）
 *   - 每行 ⋯ 菜单：删除 (GAP-F) / 拷贝 (GAP-I) — 委托给 ProjectActionMenu
 *
 * 数据源从 projectsApi.list 切到 projectsApi.query —— 后者返回
 * { data, meta:{total} } envelope，支持过滤 / 排序 / 分页。
 * 直接调 API（绕开 store）因为 toolbar/分页状态本就只在这个 view 里用，
 * store 还是给 wizard 等其它入口用的。
 */
import { onMounted, reactive, ref, computed } from "vue";
import { useRouter } from "vue-router";
import { projectsApi, type Project, type ProjectQuery } from "@/api/projects";
import { ApiError } from "@/api/client";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import EmptyState from "@/components/status/EmptyState.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";
import ProjectActionMenu from "@/components/ProjectActionMenu.vue";

const COST_PER_WAN = 10000;
const COST_DECIMALS = 2;
const PAGE_SIZE = 20;
const DEBOUNCE_MS = 250;

const router = useRouter();

// v2.0 T20 — ProjectList drives projectsApi.query() directly (bypassing the
// store) so it owns toolbar/pagination state. Store still wraps list()/create()
// for the wizard and other callers; remove() goes straight to the API here
// because no other surface needs the cached snapshot.
const items = ref<Project[]>([]);
const total = ref(0);
const page = ref(1);
const state = ref<"idle" | "loading" | "success" | "error">("idle");
const error = ref<ApiError | null>(null);

const CITIES = [
  "北京", "天津", "上海", "重庆", "石家庄", "太原", "呼和浩特", "西安", "成都",
  "昆明", "武汉", "长沙", "合肥", "长春", "沈阳", "大连", "哈尔滨", "济南",
  "青岛", "郑州", "南京", "苏州", "杭州", "宁波", "福州", "厦门", "广州",
  "深圳", "南昌", "南宁", "海口", "兰州", "贵阳", "银川", "乌鲁木齐", "拉萨", "西宁",
];
const INDUSTRIES = ["电子政务", "金融", "电信", "制造", "能源", "交通"];
const PHASES: Array<{ value: ProjectQuery["phase"]; label: string }> = [
  { value: "budget", label: "预算" },
  { value: "bidding", label: "招标" },
  { value: "planning", label: "立项" },
  { value: "change", label: "变更" },
  { value: "settled", label: "结算" },
];
const SORTS: Array<{ value: NonNullable<ProjectQuery["sort"]>; label: string }> = [
  { value: "created_at", label: "创建时间" },
  { value: "updated_at", label: "更新时间" },
  { value: "name", label: "名称" },
];

function phaseLabel(value: string | undefined): string {
  const found = PHASES.find((p) => p.value === value);
  return found?.label ?? value ?? "—";
}

const filter = reactive({
  q: "",
  city: "" as string,
  industry: "" as string,
  phase: "" as "" | NonNullable<ProjectQuery["phase"]>,
  sort: "created_at" as NonNullable<ProjectQuery["sort"]>,
  order: "desc" as NonNullable<ProjectQuery["order"]>,
});

const isLoading = computed(() => state.value === "loading" || state.value === "idle");
const isEmpty = computed(() => state.value === "success" && items.value.length === 0);
const isError = computed(() => state.value === "error");
const hasItems = computed(() => state.value === "success" && items.value.length > 0);

const totalPages = computed(() =>
  total.value === 0 ? 1 : Math.ceil(total.value / PAGE_SIZE),
);

async function reload(): Promise<void> {
  state.value = "loading";
  error.value = null;
  try {
    const result = await projectsApi.query({
      q: filter.q.trim() || undefined,
      city: filter.city || undefined,
      industry: filter.industry || undefined,
      phase: (filter.phase || undefined) as ProjectQuery["phase"],
      sort: filter.sort,
      order: filter.order,
      page: page.value,
      size: PAGE_SIZE,
    });
    items.value = result.data;
    total.value = result.meta.total;
    state.value = "success";
  } catch (e) {
    error.value = e instanceof ApiError ? e : new ApiError("UNKNOWN", String(e));
    state.value = "error";
  }
}

// 搜索输入防抖：用户连续敲键时只触发一次 query，避免噪音请求。
// 每次重置 page=1 是因为筛选条件变了再停留在原页码没意义。
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
function onSearchInput(): void {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    page.value = 1;
    void reload();
  }, DEBOUNCE_MS);
}

function onFilterChange(): void {
  page.value = 1;
  void reload();
}

function toggleOrder(): void {
  filter.order = filter.order === "asc" ? "desc" : "asc";
  page.value = 1;
  void reload();
}

function prevPage(): void {
  if (page.value > 1) {
    page.value -= 1;
    void reload();
  }
}

function nextPage(): void {
  if (page.value * PAGE_SIZE < total.value) {
    page.value += 1;
    void reload();
  }
}

function goNew(): void {
  router.push({ name: "project-wizard" });
}

function open(id: string): void {
  router.push({ name: "fp-editor", params: { id } });
}

// v2.0 T21 — delete/copy moved into ProjectActionMenu, which emits @deleted/
// @copied; we just reload() in response so the list reflects the new state.

function formatCost(value: number): string {
  return (value / COST_PER_WAN).toFixed(COST_DECIMALS);
}

onMounted(() => {
  void reload();
});
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

    <div
      class="list-toolbar"
      role="search"
      aria-label="项目筛选"
    >
      <input
        v-model="filter.q"
        type="search"
        class="search"
        placeholder="搜索项目名…"
        data-testid="filter-q"
        aria-label="搜索项目名"
        @input="onSearchInput"
      >
      <select
        v-model="filter.city"
        data-testid="filter-city"
        aria-label="城市"
        @change="onFilterChange"
      >
        <option value="">
          所有城市
        </option>
        <option
          v-for="c in CITIES"
          :key="c"
          :value="c"
        >
          {{ c }}
        </option>
      </select>
      <select
        v-model="filter.industry"
        data-testid="filter-industry"
        aria-label="行业"
        @change="onFilterChange"
      >
        <option value="">
          所有行业
        </option>
        <option
          v-for="i in INDUSTRIES"
          :key="i"
          :value="i"
        >
          {{ i }}
        </option>
      </select>
      <select
        v-model="filter.phase"
        data-testid="filter-phase"
        aria-label="阶段"
        @change="onFilterChange"
      >
        <option value="">
          所有阶段
        </option>
        <option
          v-for="p in PHASES"
          :key="p.value"
          :value="p.value"
        >
          {{ p.label }}
        </option>
      </select>
      <select
        v-model="filter.sort"
        data-testid="filter-sort"
        aria-label="排序字段"
        @change="onFilterChange"
      >
        <option
          v-for="s in SORTS"
          :key="s.value"
          :value="s.value"
        >
          {{ s.label }}
        </option>
      </select>
      <button
        type="button"
        class="btn btn-sm"
        data-testid="filter-order"
        :aria-label="filter.order === 'asc' ? '升序，点击切换为降序' : '降序，点击切换为升序'"
        @click="toggleOrder"
      >
        {{ filter.order === "asc" ? "升序 ↑" : "降序 ↓" }}
      </button>
    </div>

    <LoadingSkeleton
      v-if="isLoading"
      :rows="3"
    />

    <ErrorBanner
      v-else-if="isError"
      :problem="'无法加载项目列表'"
      :cause="error?.message ?? '未知错误'"
      :suggestion="'请检查后端服务是否启动后重试'"
      :retryable="true"
      @retry="reload"
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
        v-for="p in items"
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
            <dd>{{ phaseLabel(p.phase) }}</dd>
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
          <ProjectActionMenu
            :project-id="p.id"
            :project-name="p.name"
            @deleted="reload"
            @copied="reload"
          />
        </footer>
      </li>
    </ul>

    <nav
      v-if="hasItems && total > PAGE_SIZE"
      class="pagination"
      aria-label="分页"
    >
      <button
        type="button"
        class="btn btn-sm"
        :disabled="page <= 1"
        data-testid="pagination-prev"
        @click="prevPage"
      >
        上一页
      </button>
      <span class="pagination-info">
        第 {{ page }} / {{ totalPages }} 页（共 {{ total }} 条）
      </span>
      <button
        type="button"
        class="btn btn-sm"
        :disabled="page * PAGE_SIZE >= total"
        data-testid="pagination-next"
        @click="nextPage"
      >
        下一页
      </button>
    </nav>
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
.list-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-3);
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: var(--radius-md, 8px);
}
.list-toolbar .search {
  flex: 1 1 220px;
  min-width: 180px;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: var(--radius-sm, 6px);
  font-size: var(--font-size-sm);
  background: var(--color-surface, #fff);
  color: var(--color-text-body);
}
.list-toolbar select {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: var(--radius-sm, 6px);
  font-size: var(--font-size-sm);
  background: var(--color-surface, #fff);
  color: var(--color-text-body);
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
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-2) 0;
}
.pagination-info {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}
</style>
