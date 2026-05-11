<script setup lang="ts">
/**
 * ProjectList — v2.2 重做：KPI 看板 + 筛选栏 + table/card 双视图
 *
 * 主要变化（相对 v2.0）：
 *   - 顶部 KPI 卡片行（KpiCardRow）：汇总全部/草稿/计算中/已归档，点卡片即筛选
 *   - ProjectFilterBar 替换原 list-toolbar（城市/行业/阶段 + table/card 切换）
 *   - table 视图：点行跳转（.row-link），替代旧"打开"按钮
 *   - card 视图：网格卡片
 *   - status 字段从 total_fp / total_cost 派生（服务端无 status 字段）
 */
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { projectsApi, type Project, type ProjectQuery } from "@/api/projects";
import { statsApi, type ProjectStats } from "@/api/stats";
import { ApiError } from "@/api/client";
import KpiCardRow from "@/components/projects/KpiCardRow.vue";
import ProjectFilterBar from "@/components/projects/ProjectFilterBar.vue";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import EmptyState from "@/components/status/EmptyState.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";
import ProjectActionMenu from "@/components/ProjectActionMenu.vue";

const COST_PER_WAN = 10000;
const PAGE_SIZE = 50;

const router = useRouter();
const items = ref<Project[]>([]);
const total = ref(0);
const stats = ref<ProjectStats | null>(null);
const page = ref(1);
const state = ref<"idle" | "loading" | "success" | "error">("idle");
const error = ref<ApiError | null>(null);

// KPI filter (client-side)
const filterStatus = ref<string>("全部");
// Filter bar (server-side via API)
const filterCity = ref<string | null>(null);
const filterIndustry = ref<string | null>(null);
const filterPhase = ref<string | null>(null);
const search = ref<string>("");
// View toggle
const view = ref<"table" | "card">("table");

/** 从 total_fp / total_cost 派生状态（服务端无 status 字段） */
function deriveStatus(p: Project): "草稿" | "计算中" | "已计算" {
  if (!p.total_fp) return "草稿";
  if (!p.total_cost) return "计算中";
  return "已计算";
}

const filtered = computed(() => {
  let xs = items.value;

  // KPI 卡片筛选
  if (filterStatus.value === "草稿") {
    xs = xs.filter((p) => deriveStatus(p) === "草稿");
  } else if (filterStatus.value === "计算中") {
    xs = xs.filter((p) => {
      const s = deriveStatus(p);
      return s === "计算中" || s === "已计算";
    });
  } else if (filterStatus.value === "已归档") {
    xs = []; // 未实现
  }

  // 搜索
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    xs = xs.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.id.toLowerCase().includes(q) ||
        (p.client ?? "").toLowerCase().includes(q)
    );
  }

  return xs;
});

const phaseLabel: Record<string, string> = {
  budget: "预算编制",
  bidding: "招投标",
  planning: "立项审批",
  change: "变更评估",
  settled: "结算审计",
};

async function load(): Promise<void> {
  state.value = "loading";
  error.value = null;
  try {
    const q: ProjectQuery = {
      page: page.value,
      size: PAGE_SIZE,
      city: filterCity.value ?? undefined,
      industry: filterIndustry.value ?? undefined,
      phase: (filterPhase.value || undefined) as ProjectQuery["phase"],
    };
    const res = await projectsApi.query(q);
    items.value = res.data;
    total.value = res.meta.total;
    state.value = "success";
  } catch (e) {
    error.value =
      e instanceof ApiError ? e : new ApiError("LOAD_FAILED", "加载失败");
    state.value = "error";
  }
}

async function loadStats(): Promise<void> {
  try {
    stats.value = await statsApi.getProjectStats();
  } catch {
    // KPI 失败不阻断主流程
  }
}

onMounted(() => {
  void load();
  void loadStats();
});

function onFilter(key: string): void {
  filterStatus.value = key;
}

function onOpen(p: Project): void {
  router.push(`/projects/${p.id}/functions`);
}

function onNew(): void {
  router.push({ name: "project-wizard" });
}

function fmtWan(n: number | null | undefined): string {
  if (n == null) return "—";
  return (n / COST_PER_WAN).toFixed(2);
}

function modeLabel(m: string): string {
  return m === "reverse" ? "反向反推" : "正向估算";
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">项目工作台</h1>
        <div class="page-sub">
          软件造价咨询项目 · GB/T 36964-2018 + CSBMK®-202510
        </div>
      </div>
      <div class="page-spacer" />
      <button type="button" class="btn btn-ghost">导入</button>
      <button type="button" class="btn btn-ghost">批量导出</button>
      <button type="button" class="btn btn-primary" @click="onNew">
        + 新建项目
      </button>
    </div>

    <KpiCardRow
      v-if="stats"
      :stats="stats"
      :active-filter="filterStatus"
      @filter="onFilter"
    />

    <ProjectFilterBar
      v-model:city="filterCity"
      v-model:industry="filterIndustry"
      v-model:phase="filterPhase"
      v-model:view="view"
      :total="total"
      :filtered="filtered.length"
    />

    <ErrorBanner
      v-if="error"
      :problem="'无法加载项目列表'"
      :cause="error.message"
      :suggestion="'请检查后端服务是否启动后重试'"
      :retryable="true"
      @retry="load"
    />

    <LoadingSkeleton v-if="state === 'loading'" :rows="3" />

    <EmptyState
      v-else-if="filtered.length === 0"
      :title="'暂无项目'"
      :description="filterStatus !== '全部' ? '当前筛选条件下没有项目' : '创建你的第一个造价评估项目'"
      :cta-label="filterStatus === '全部' ? '新建第一个项目' : undefined"
      @cta-click="onNew"
    />

    <!-- 表格视图 -->
    <div
      v-else-if="view === 'table'"
      class="card"
      style="padding: 0; overflow: hidden"
    >
      <table class="table">
        <thead>
          <tr>
            <th>项目名 / 编码</th>
            <th>模式</th>
            <th>客户 · 城市 · 行业</th>
            <th>阶段</th>
            <th style="text-align: right">规模 (FP)</th>
            <th style="text-align: right">P50 造价</th>
            <th>状态</th>
            <th>更新时间</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="p in filtered"
            :key="p.id"
            class="row-link"
            :data-project-id="p.id"
            @click="onOpen(p)"
          >
            <td>
              <div style="font-weight: 500">{{ p.name }}</div>
              <div class="muted mono" style="font-size: 11px">{{ p.id }}</div>
            </td>
            <td>
              <span
                class="badge"
                :class="
                  p.mode === 'reverse' ? 'badge-amber' : 'badge-blue'
                "
              >{{ modeLabel(p.mode) }}</span>
            </td>
            <td>
              <div style="font-size: 12px">{{ p.client ?? "—" }}</div>
              <div class="muted" style="font-size: 11px">
                {{ p.city }} · {{ p.industry }}
              </div>
            </td>
            <td>
              <span class="chip">{{ phaseLabel[p.phase] ?? p.phase }}</span>
            </td>
            <td class="mono" style="text-align: right">
              {{ p.total_fp ?? "—" }}
            </td>
            <td class="mono" style="text-align: right; font-weight: 500">
              <span v-if="p.total_cost">¥{{ fmtWan(p.total_cost) }}万</span>
              <span v-else class="muted">—</span>
            </td>
            <td>
              <span class="badge">{{ deriveStatus(p) }}</span>
            </td>
            <td class="muted mono" style="font-size: 11px">
              {{ p.updated_at.slice(0, 16) }}
            </td>
            <td @click.stop>
              <ProjectActionMenu
                :project-id="p.id"
                :project-name="p.name"
                @deleted="load"
                @copied="load"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 卡片视图 -->
    <div v-else class="card-grid">
      <div
        v-for="p in filtered"
        :key="p.id"
        class="card card-tile"
        @click="onOpen(p)"
      >
        <div class="card-tile-head">
          <div>
            <div style="font-weight: 600; font-size: 14px">{{ p.name }}</div>
            <div class="muted mono" style="font-size: 11px">{{ p.id }}</div>
          </div>
          <span
            class="badge"
            :class="p.mode === 'reverse' ? 'badge-amber' : 'badge-blue'"
          >{{ modeLabel(p.mode) }}</span>
        </div>
        <div class="card-tile-chips">
          <span class="chip">{{ p.city }}</span>
          <span class="chip">{{ p.industry }}</span>
          <span class="chip">{{ phaseLabel[p.phase] ?? p.phase }}</span>
        </div>
        <div class="card-tile-foot">
          <div>
            <div class="muted" style="font-size: 11px">规模</div>
            <div class="mono">{{ p.total_fp ?? "—" }} FP</div>
          </div>
          <div style="text-align: right">
            <div class="muted" style="font-size: 11px">P50 造价</div>
            <div
              class="mono"
              style="font-weight: 600; color: var(--accent)"
            >
              {{ p.total_cost ? `¥${fmtWan(p.total_cost)}万` : "—" }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.page-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.page-title {
  margin: 0;
  font-size: var(--font-size-xl, 20px);
  font-weight: 700;
  color: var(--color-text-title, var(--text));
}
.page-sub {
  font-size: 12px;
  color: var(--color-text-muted, var(--text-3));
  margin-top: 2px;
}
.page-spacer {
  flex: 1;
}

/* Card grid (card view) */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}
.card-tile {
  padding: 18px;
  cursor: pointer;
  transition: border-color var(--duration-fast, 150ms);
}
.card-tile:hover {
  border-color: var(--accent, var(--color-primary));
}
.card-tile-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}
.card-tile-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.card-tile-foot {
  display: flex;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--border, var(--color-border));
}

/* Table row link */
.row-link {
  cursor: pointer;
}
.row-link:hover td {
  background: var(--color-primary-bg, var(--accent-soft));
}
</style>
