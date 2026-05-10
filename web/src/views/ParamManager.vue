<script setup lang="ts">
import { onMounted, ref, computed, watch } from "vue";
import { useParamsStore } from "@/stores/params";
import { useResultsStore } from "@/stores/results";
import OverrideField from "@/components/OverrideField.vue";
import FactorTable from "@/components/FactorTable.vue";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";
import { snapshotsApi, type ParamSnapshot } from "@/api/snapshots";

const props = defineProps<{ projectId: string }>();

const store = useParamsStore();
const results = useResultsStore();

const activeTab = ref<string>("rate");
const loading = ref(true);
const error = ref<string | null>(null);

// GAP-H — 快照 tab 状态
const snapshots = ref<ParamSnapshot[]>([]);
const newSnapLabel = ref<string>("");
const snapshotsLoading = ref<boolean>(false);
const snapshotsError = ref<string | null>(null);

async function reloadSnapshots(): Promise<void> {
  snapshotsLoading.value = true;
  snapshotsError.value = null;
  try {
    snapshots.value = await snapshotsApi.list("global");
  } catch (e: unknown) {
    snapshotsError.value = e instanceof Error ? e.message : "快照加载失败";
  } finally {
    snapshotsLoading.value = false;
  }
}

async function onCreateSnapshot(): Promise<void> {
  const label = newSnapLabel.value.trim();
  try {
    await snapshotsApi.create({
      scope: "global",
      label: label || undefined,
    });
    newSnapLabel.value = "";
    await reloadSnapshots();
  } catch (e: unknown) {
    snapshotsError.value = e instanceof Error ? e.message : "创建快照失败";
  }
}

async function onRestoreSnapshot(id: number): Promise<void> {
  if (!window.confirm("确定恢复到这一时刻的参数？当前未保存的修改会被覆盖。")) return;
  try {
    await snapshotsApi.restore(id);
    // 恢复后重新拉 effective，让其他 tab 同步刷新
    await store.loadFor(props.projectId);
    results.markParamsChanged();
    await reloadSnapshots();
  } catch (e: unknown) {
    snapshotsError.value = e instanceof Error ? e.message : "恢复快照失败";
  }
}

async function onDeleteSnapshot(id: number): Promise<void> {
  if (!window.confirm("删除这个快照？此操作不可撤销。")) return;
  try {
    await snapshotsApi.remove(id);
    await reloadSnapshots();
  } catch (e: unknown) {
    snapshotsError.value = e instanceof Error ? e.message : "删除快照失败";
  }
}

function formatSnapshotTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

// 切到 snapshots tab 时拉列表（懒加载，避免初始加载多发请求）
watch(activeTab, (v) => {
  if (v === "snapshots") {
    void reloadSnapshots();
  }
});

const PRODUCTIVITY_BANDS = ["P10", "P50", "P90"] as const;
type Band = (typeof PRODUCTIVITY_BANDS)[number];

async function load(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    await store.loadFor(props.projectId);
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "加载失败";
  } finally {
    loading.value = false;
  }
}

onMounted(load);

const TABS = [
  { id: "rate", label: "费率" },
  { id: "productivity", label: "生产率" },
  { id: "factors_dev", label: "开发因子" },
  { id: "factors_ops", label: "运维因子" },
  { id: "scale_change", label: "规模变更" },
  { id: "snapshots", label: "快照" },
] as const;

const eff = computed(() => store.effective);

async function patchOverride(key: string, value: unknown): Promise<void> {
  await store.applyOverride(props.projectId, { [key]: value });
  results.markParamsChanged();
}

// 规模变更因子展示标签 — 处理需求 增加 / 减少 / 修改 / 转换 / 变更率门槛
const SCALE_CHANGE_LABELS: Record<string, string> = {
  add: "新增",
  remove: "删除",
  modify: "修改",
  convert: "转换",
  threshold: "变更率门槛",
};

// 因子展示标签 — key 名为 CSBMK 数据中的 factor name，value 为中文显示名
const FACTOR_LABELS: Record<string, string> = {
  // factors_dev
  app_type: "应用类型",
  integrity_level: "完整性等级",
  non_func: "非功能性要求",
  platform: "运行平台",
  team_bg: "团队背景",
  // factors_ops
  update_freq: "更新频率",
  support: "支持方式",
  security_level: "安全等级",
  business_importance: "业务重要性",
  response_time: "响应时间",
  team_exp: "团队经验",
  automation: "自动化程度",
  deployment: "部署方式",
  user_scale: "用户规模",
  system_relevance: "关联系统数",
};

interface FactorLevel {
  multiplier: number;
  description?: string;
}

/**
 * CSBMK 中 factors_dev / factors_ops 的 level value 是直接数字 (e.g. 1.0)，
 * FactorTable 期望 { multiplier: number } 形态。这里做适配。
 */
function normalizeLevels(
  rawLevels: Record<string, unknown>,
): Record<string, FactorLevel> {
  const out: Record<string, FactorLevel> = {};
  for (const [k, v] of Object.entries(rawLevels)) {
    if (typeof v === "number") {
      out[k] = { multiplier: v };
    } else if (
      v &&
      typeof v === "object" &&
      typeof (v as { multiplier?: unknown }).multiplier === "number"
    ) {
      out[k] = {
        multiplier: (v as { multiplier: number }).multiplier,
        description: (v as { description?: string }).description,
      };
    }
  }
  return out;
}

async function onFactorEdit(
  group: "factors_dev" | "factors_ops",
  factorName: string,
  payload: { levelKey: string; value: number },
): Promise<void> {
  // CSBMK 数据中 level 值为直接数字，path = "{group}.{factor}.{level}"，
  // 末端是 scalar — 与 _path_resolves_to_leaf 校验吻合。
  const path = `${group}.${factorName}.${payload.levelKey}`;
  await patchOverride(path, payload.value);
}
</script>

<template>
  <section
    class="page"
    aria-labelledby="title"
  >
    <header class="page-header">
      <h1 id="title">
        参数管理
      </h1>
    </header>

    <LoadingSkeleton
      v-if="loading"
      :rows="6"
    />

    <ErrorBanner
      v-else-if="error"
      :problem="'参数加载失败'"
      :cause="error"
      :suggestion="'请刷新后重试'"
      :retryable="true"
      @retry="load"
    />

    <div
      v-else
      class="card param-card"
    >
      <div
        role="tablist"
        class="tabs"
      >
        <button
          v-for="t in TABS"
          :key="t.id"
          type="button"
          role="tab"
          class="tab"
          :aria-selected="activeTab === t.id"
          :data-active="activeTab === t.id"
          @click="activeTab = t.id"
        >
          {{ t.label }}
        </button>
      </div>

      <section
        v-if="activeTab === 'rate' && eff"
        role="tabpanel"
        class="panel"
      >
        <h2>城市费率（元/人月）</h2>
        <p class="hint">
          基于 CSBMK®-202510，可单项覆盖。开发与运维各自独立费率。
        </p>
        <div class="city-rate-list">
          <div
            v-for="(rate, city) in eff.city_rate"
            :key="String(city)"
            class="city-rate-row"
            data-testid="city-rate-row"
          >
            <div class="city-rate-city">
              {{ city }}
            </div>
            <OverrideField
              :label="`${city}（开发）`"
              :model-value="rate.dev"
              :default-value="rate.dev"
              :overridden="store.isOverridden(`city_rate.${String(city)}.dev`)"
              @update:model-value="(nv) => patchOverride(`city_rate.${String(city)}.dev`, nv)"
            />
            <OverrideField
              :label="`${city}（运维）`"
              :model-value="rate.ops"
              :default-value="rate.ops"
              :overridden="store.isOverridden(`city_rate.${String(city)}.ops`)"
              @update:model-value="(nv) => patchOverride(`city_rate.${String(city)}.ops`, nv)"
            />
          </div>
        </div>
      </section>

      <section
        v-else-if="activeTab === 'productivity' && eff"
        role="tabpanel"
        class="panel"
      >
        <h3 class="subtitle">
          开发生产率（FP/人月）
        </h3>
        <div class="grid">
          <template
            v-for="(bands, ind) in eff.productivity_dev"
            :key="`dev-${String(ind)}`"
          >
            <OverrideField
              v-for="band in PRODUCTIVITY_BANDS"
              :key="`dev-${String(ind)}-${band}`"
              :label="`${String(ind)} ${band}`"
              :model-value="(bands as Record<Band, number>)[band]"
              :default-value="(bands as Record<Band, number>)[band]"
              :overridden="store.isOverridden(`productivity_dev.${String(ind)}.${band}`)"
              @update:model-value="(nv) => patchOverride(`productivity_dev.${String(ind)}.${band}`, nv)"
            />
          </template>
        </div>
        <h3
          v-if="eff.productivity_ops && Object.keys(eff.productivity_ops).length > 0"
          class="subtitle subtitle-spaced"
        >
          运维生产率（FP/人月）
        </h3>
        <div
          v-if="eff.productivity_ops && Object.keys(eff.productivity_ops).length > 0"
          class="grid"
        >
          <template
            v-for="(bands, ind) in eff.productivity_ops"
            :key="`ops-${String(ind)}`"
          >
            <OverrideField
              v-for="band in PRODUCTIVITY_BANDS"
              :key="`ops-${String(ind)}-${band}`"
              :label="`${String(ind)} ${band}`"
              :model-value="(bands as Record<Band, number>)[band]"
              :default-value="(bands as Record<Band, number>)[band]"
              :overridden="store.isOverridden(`productivity_ops.${String(ind)}.${band}`)"
              @update:model-value="(nv) => patchOverride(`productivity_ops.${String(ind)}.${band}`, nv)"
            />
          </template>
        </div>
      </section>

      <section
        v-else-if="activeTab === 'factors_dev' && eff && eff.factors_dev"
        role="tabpanel"
        class="panel"
      >
        <h2>开发调整因子</h2>
        <p class="hint">
          开发工作量调整因子 — 各因子按所选级别系数链式相乘后作用于开发工作量。
        </p>
        <FactorTable
          v-for="(levels, factorName) in eff.factors_dev"
          :key="`dev-${String(factorName)}`"
          :factor="{
            name: String(factorName),
            label: FACTOR_LABELS[String(factorName)] ?? String(factorName),
            levels: normalizeLevels(levels as Record<string, unknown>),
          }"
          scope="global"
          @update:multiplier="(payload) => onFactorEdit('factors_dev', String(factorName), payload)"
        />
      </section>

      <section
        v-else-if="activeTab === 'scale_change' && eff && eff.scale_change"
        role="tabpanel"
        class="panel"
      >
        <h2>规模变更因子</h2>
        <p class="hint">
          规模变更因子 — 处理需求增加 / 减少 / 修改 / 转换的场景。
        </p>
        <table class="rate-table">
          <thead>
            <tr>
              <th>变更类型</th>
              <th>因子值</th>
            </tr>
          </thead>
          <tbody>
            <template
              v-for="(value, key) in eff.scale_change"
              :key="String(key)"
            >
              <tr v-if="typeof value === 'number'">
                <td>{{ SCALE_CHANGE_LABELS[String(key)] ?? String(key) }}</td>
                <td>
                  <OverrideField
                    :label="SCALE_CHANGE_LABELS[String(key)] ?? String(key)"
                    :model-value="value as number"
                    :default-value="value as number"
                    :overridden="store.isOverridden(`scale_change.${String(key)}`)"
                    @update:model-value="(nv) => patchOverride(`scale_change.${String(key)}`, nv)"
                  />
                </td>
              </tr>
              <tr
                v-for="(sub, subKey) in (value as Record<string, number>)"
                v-else
                :key="`${String(key)}.${String(subKey)}`"
              >
                <td>
                  {{ SCALE_CHANGE_LABELS[String(key)] ?? String(key) }}
                  /
                  {{ SCALE_CHANGE_LABELS[String(subKey)] ?? String(subKey) }}
                </td>
                <td>
                  <OverrideField
                    :label="`${String(key)}/${String(subKey)}`"
                    :model-value="sub"
                    :default-value="sub"
                    :overridden="store.isOverridden(`scale_change.${String(key)}.${String(subKey)}`)"
                    @update:model-value="(nv) => patchOverride(`scale_change.${String(key)}.${String(subKey)}`, nv)"
                  />
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </section>

      <section
        v-else-if="activeTab === 'factors_ops' && eff && eff.factors_ops"
        role="tabpanel"
        class="panel"
      >
        <h2>运维调整因子</h2>
        <p class="hint">
          运维工作量调整因子 — 各因子按所选级别系数链式相乘后作用于运维工作量。
        </p>
        <FactorTable
          v-for="(levels, factorName) in eff.factors_ops"
          :key="`ops-${String(factorName)}`"
          :factor="{
            name: String(factorName),
            label: FACTOR_LABELS[String(factorName)] ?? String(factorName),
            levels: normalizeLevels(levels as Record<string, unknown>),
          }"
          scope="global"
          @update:multiplier="(payload) => onFactorEdit('factors_ops', String(factorName), payload)"
        />
      </section>

      <section
        v-else-if="activeTab === 'snapshots'"
        role="tabpanel"
        class="panel"
      >
        <h2>参数快照</h2>
        <p class="hint">
          参数快照可在重要节点固化当前全局参数；后续可恢复到任一快照点。
        </p>
        <div class="snap-toolbar">
          <input
            v-model="newSnapLabel"
            class="snap-label-input"
            type="text"
            placeholder="备注（可选，如 实验前 / before-edit）"
            maxlength="120"
          >
          <button
            type="button"
            class="btn-primary"
            @click="onCreateSnapshot"
          >
            立即快照
          </button>
        </div>
        <div
          v-if="snapshotsError"
          role="alert"
          class="snap-error"
        >
          {{ snapshotsError }}
        </div>
        <table class="rate-table snap-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>备注</th>
              <th>创建时间</th>
              <th>作用域</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="s in snapshots"
              :key="s.id"
              data-testid="snapshot-row"
            >
              <td>#{{ s.id }}</td>
              <td>{{ s.label || "—" }}</td>
              <td>{{ formatSnapshotTime(s.created_at) }}</td>
              <td>{{ s.scope }}</td>
              <td class="snap-actions">
                <button
                  type="button"
                  class="btn-secondary"
                  @click="onRestoreSnapshot(s.id)"
                >
                  恢复
                </button>
                <button
                  type="button"
                  class="btn-link"
                  @click="onDeleteSnapshot(s.id)"
                >
                  删除
                </button>
              </td>
            </tr>
            <tr v-if="snapshots.length === 0 && !snapshotsLoading">
              <td
                colspan="5"
                class="empty"
              >
                暂无快照
              </td>
            </tr>
            <tr v-else-if="snapshotsLoading && snapshots.length === 0">
              <td
                colspan="5"
                class="empty"
              >
                加载中…
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section
        v-else
        role="tabpanel"
        class="panel"
      >
        <h2>{{ TABS.find((t) => t.id === activeTab)?.label }}</h2>
        <p class="hint">
          该 Tab 内容将在 v2 完成（当前阶段仅展示骨架）。
        </p>
      </section>
    </div>
  </section>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.page-header h1 {
  margin: 0;
}
.param-card {
  padding: 0;
  display: flex;
  flex-direction: column;
}
.tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-hover);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  overflow: hidden;
}
.tab {
  height: var(--touch-target-comfortable);
  padding: 0 var(--space-4);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--color-text-body);
  font-family: inherit;
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}
.tab:hover {
  color: var(--color-primary);
  background: var(--color-primary-bg);
}
.tab[data-active="true"] {
  border-bottom-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-bg-elevated);
}
.panel {
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.panel h2 {
  margin: 0;
  font-size: var(--font-size-md);
}
.hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  margin: 0;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space-2);
}
.subtitle {
  margin: 0;
  font-size: var(--font-size-md);
  color: var(--color-text-body);
  font-weight: 600;
}
.subtitle-spaced {
  margin-top: var(--space-5);
}
.city-rate-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.city-rate-row {
  display: grid;
  grid-template-columns: minmax(80px, auto) 1fr 1fr;
  gap: var(--space-3);
  align-items: start;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border);
}
.city-rate-row:last-child {
  border-bottom: none;
}
.city-rate-city {
  font-weight: 600;
  color: var(--color-text-body);
  padding-top: var(--space-2);
}
.rate-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}
.rate-table thead th {
  text-align: left;
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-weight: 600;
}
.rate-table tbody td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}
.rate-table tbody tr:last-child td {
  border-bottom: none;
}
.rate-table tbody td:first-child {
  font-weight: 500;
  color: var(--color-text-body);
  white-space: nowrap;
}

/* GAP-H — 快照 tab 样式 */
.snap-toolbar {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-2) 0;
}
.snap-label-input {
  flex: 1 1 auto;
  min-width: 0;
  height: var(--touch-target-comfortable);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  color: var(--color-text-body);
  font-family: inherit;
  font-size: var(--font-size-sm);
  transition: border-color var(--duration-fast) var(--ease-out);
}
.snap-label-input:focus {
  outline: none;
  border-color: var(--color-primary);
}
.snap-error {
  padding: var(--space-2) var(--space-3);
  background: var(--color-danger-bg, #fef2f2);
  color: var(--color-danger, #b91c1c);
  border: 1px solid var(--color-danger-border, #fecaca);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
}
.snap-table tbody td.empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-4) var(--space-3);
  font-style: italic;
}
.snap-actions {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}
.snap-actions .btn-link {
  background: transparent;
  border: none;
  color: var(--color-danger, #b91c1c);
  cursor: pointer;
  padding: var(--space-1) var(--space-2);
  font-family: inherit;
  font-size: var(--font-size-sm);
  text-decoration: underline;
  transition: opacity var(--duration-fast) var(--ease-out);
}
.snap-actions .btn-link:hover {
  opacity: 0.75;
}
</style>
