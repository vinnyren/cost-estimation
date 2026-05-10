<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useParamsStore } from "@/stores/params";
import { useResultsStore } from "@/stores/results";
import OverrideField from "@/components/OverrideField.vue";
import FactorTable from "@/components/FactorTable.vue";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";

const props = defineProps<{ projectId: string }>();

const store = useParamsStore();
const results = useResultsStore();

const activeTab = ref<string>("rate");
const loading = ref(true);
const error = ref<string | null>(null);

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
</style>
