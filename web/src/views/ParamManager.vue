<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useParamsStore } from "@/stores/params";
import { useResultsStore } from "@/stores/results";
import OverrideField from "@/components/OverrideField.vue";
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
          基于 CSBMK®-202510，可单项覆盖。
        </p>
        <div class="grid">
          <OverrideField
            v-for="(rate, city) in eff.city_rate"
            :key="city"
            :label="`${city}（开发）`"
            :model-value="rate.dev"
            :default-value="rate.dev"
            :overridden="store.isOverridden(`city_rate.${String(city)}.dev`)"
            @update:model-value="(nv) => patchOverride(`city_rate.${String(city)}.dev`, nv)"
          />
        </div>
      </section>

      <section
        v-else-if="activeTab === 'productivity' && eff"
        role="tabpanel"
        class="panel"
      >
        <h2>开发生产率（FP/人月）</h2>
        <div class="grid">
          <template
            v-for="(bands, ind) in eff.productivity_dev"
            :key="ind"
          >
            <OverrideField
              v-for="band in PRODUCTIVITY_BANDS"
              :key="`${String(ind)}-${band}`"
              :label="`${String(ind)} ${band}`"
              :model-value="(bands as Record<Band, number>)[band]"
              :default-value="(bands as Record<Band, number>)[band]"
              :overridden="store.isOverridden(`productivity_dev.${String(ind)}.${band}`)"
              @update:model-value="(nv) => patchOverride(`productivity_dev.${String(ind)}.${band}`, nv)"
            />
          </template>
        </div>
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
</style>
