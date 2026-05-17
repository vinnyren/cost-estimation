<script setup lang="ts">
/**
 * AllocatorPanel — 反算分摊面板。
 *
 * 单一规模模型：反算产出一个功能点规模（开发与运维共用）。这里：
 *   - 模块列表 = 项目真实 FP 的一级模块（l1_module 分组）
 *   - 「生成分摊」把推荐档目标规模 US 按权重分到各 l1 模块
 *   - 「写回 FP 表」把每个模块分配的 US 按该模块下各 FP 的现有 US 占比拆下去，
 *     逐条 PATCH function_points.us。写回后正向计算可精确复现反算目标总额。
 */
import { ref, computed, onMounted } from "vue";
import { calcApi, type AllocateResult, type ReverseResult, type Band } from "@/api/calc";
import { functionsApi, type FunctionPoint } from "@/api/functions";

interface DraftRow {
  name: string;
  weight: number;
  locked: boolean;
  locked_us: number;
}

const props = defineProps<{
  reverseResult: ReverseResult;
  projectId: string;
}>();

const emit = defineEmits<{
  allocated: [result: AllocateResult];
  "fp-updated": [count: number];
}>();

const UNGROUPED = "未分组";

const allFps = ref<FunctionPoint[]>([]);
const drafts = ref<DraftRow[]>([]);
const allocResult = ref<AllocateResult | null>(null);
const allocating = ref(false);
const writingBack = ref(false);
const hint = ref<string>("");
const writeBackBanner = ref<string>("");

/** 按 l1_module 分组：模块名 → FP 列表。 */
function groupByModule(fps: FunctionPoint[]): Map<string, FunctionPoint[]> {
  const groups = new Map<string, FunctionPoint[]>();
  for (const fp of fps) {
    const mod = fp.l1_module?.trim() || UNGROUPED;
    const list = groups.get(mod) ?? [];
    list.push(fp);
    groups.set(mod, list);
  }
  return groups;
}

/** 重建 drafts —— weight 初值取该模块现有 US 总和，保留真实结构占比。 */
function rebuildDrafts(): void {
  const groups = groupByModule(allFps.value);
  drafts.value = [...groups.entries()].map(([name, fps]) => ({
    name,
    weight: fps.reduce((s, fp) => s + fp.us, 0),
    locked: false,
    locked_us: 0,
  }));
  allocResult.value = null;
  writeBackBanner.value = "";
  hint.value = "";
}

onMounted(async () => {
  try {
    allFps.value = await functionsApi.list(props.projectId);
  } catch (e: unknown) {
    hint.value = e instanceof Error ? e.message : "功能点加载失败";
  }
  rebuildDrafts();
});

const hasFps = computed(() => allFps.value.length > 0);
const canAllocate = computed(
  () => drafts.value.length > 0 && drafts.value.every((d) => d.name.trim()),
);

function targetUs(): number | null {
  const band: Band = props.reverseResult.recommended_band ?? "P50";
  const us = props.reverseResult.scale_adjusted_bands?.[band];
  return us && us > 0 ? us : null;
}

async function onGenerate(): Promise<void> {
  if (!canAllocate.value) {
    hint.value = "请确保所有模块都填写名称。";
    return;
  }
  const us = targetUs();
  if (us === null) {
    hint.value = "反算结果无可用推荐档规模，请重算 reverse。";
    return;
  }
  allocating.value = true;
  hint.value = "";
  writeBackBanner.value = "";
  try {
    const res = await calcApi.allocate({
      project_id: props.projectId,
      target_us: us,
      cf: props.reverseResult.cf_used,
      drafts: drafts.value.map((d) => ({
        name: d.name,
        weight: d.weight,
        locked: d.locked,
        locked_us: d.locked_us,
      })),
    });
    allocResult.value = res;
    emit("allocated", res);
  } catch (e: unknown) {
    hint.value = e instanceof Error ? e.message : "分摊失败";
  } finally {
    allocating.value = false;
  }
}

/**
 * 写回：把每个分摊模块的 US 按该模块下各 FP 现有 US 占比拆下去，逐条 PATCH。
 * 模块现 US 总和为 0 时平均分配。
 */
async function onWriteBack(): Promise<void> {
  if (!allocResult.value) return;
  const groups = groupByModule(allFps.value);

  const patches: Array<{ id: string; us: number }> = [];
  for (const item of allocResult.value.items) {
    const fps = groups.get(item.name);
    if (!fps || fps.length === 0) continue;
    const moduleTotal = fps.reduce((s, fp) => s + fp.us, 0);
    for (const fp of fps) {
      const newUs =
        moduleTotal > 0
          ? item.us * (fp.us / moduleTotal)
          : item.us / fps.length;
      patches.push({ id: fp.id, us: newUs });
    }
  }

  if (patches.length === 0) {
    writeBackBanner.value = "";
    hint.value = "没有可写回的功能点（分摊模块与 FP 模块不匹配）。";
    return;
  }

  const ok = window.confirm(
    `将按分摊结果更新 ${patches.length} 条功能点的规模，是否继续？`,
  );
  if (!ok) return;

  writingBack.value = true;
  hint.value = "";
  try {
    await Promise.all(
      patches.map((p) => functionsApi.patch(props.projectId, p.id, { us: p.us })),
    );
    // 写回后刷新本地 FP 缓存，让占比基于最新值（重复写回时正确）。
    allFps.value = await functionsApi.list(props.projectId);
    writeBackBanner.value = `已写回 ${patches.length} 条 FP`;
    emit("fp-updated", patches.length);
  } catch (e: unknown) {
    hint.value = e instanceof Error ? e.message : "写回失败";
  } finally {
    writingBack.value = false;
  }
}
</script>

<template>
  <div class="card allocator-panel">
    <div class="allocator-head">
      <div class="section-title">FP 模块反算分摊</div>
      <div class="muted" style="font-size: 12px">
        模块来自项目真实功能点的一级模块；分摊后可按现有规模比例写回每条 FP，
        写回后正向计算可精确复现反算目标
      </div>
    </div>

    <div v-if="!hasFps" class="banner banner-amber" style="margin-top: 12px">
      项目暂无功能点 —— 请先在 FP 编辑页上传文档让 AI 生成，或手动添加功能点。
    </div>

    <template v-else>
      <table class="table allocator-drafts">
        <thead>
          <tr>
            <th>一级模块</th>
            <th style="width: 200px">权重（现有规模合计）</th>
            <th style="width: 110px">锁定 FP</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(d, idx) in drafts" :key="idx">
            <td><b>{{ d.name }}</b></td>
            <td>
              <input
                class="field-input mono"
                type="number"
                min="0"
                step="0.5"
                v-model.number="d.weight"
              />
            </td>
            <td>
              <input
                class="field-input mono"
                type="number"
                min="0"
                step="0.5"
                v-model.number="d.locked_us"
                placeholder="0"
              />
            </td>
          </tr>
        </tbody>
      </table>

      <div class="allocator-actions">
        <div style="flex: 1" />
        <button
          class="btn btn-primary"
          :disabled="!canAllocate || allocating"
          @click="onGenerate"
        >
          {{ allocating ? "生成中…" : "✨ 生成分摊" }}
        </button>
      </div>
    </template>

    <div v-if="hint" class="banner banner-amber" style="margin-top: 12px">{{ hint }}</div>

    <template v-if="allocResult">
      <div class="section-head" style="margin-top: 20px">
        <div class="section-title">分摊结果</div>
      </div>
      <table class="table allocator-result">
        <thead>
          <tr>
            <th>模块</th>
            <th style="text-align: right">分配规模</th>
            <th style="width: 80px">锁定</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, idx) in allocResult.items" :key="idx">
            <td><b>{{ r.name }}</b></td>
            <td class="mono" style="text-align: right; font-weight: 500">{{ r.us.toFixed(2) }}</td>
            <td>
              <span v-if="r.locked" class="badge badge-amber">已锁定</span>
              <span v-else class="muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="banner banner-green" style="margin-top: 12px">
        ✓ 双向一致性校验
        · 反算总规模 <b class="mono">{{ allocResult.validation.recalc_total_us.toFixed(2) }}</b>
        · 调整后 <b class="mono">{{ allocResult.validation.recalc_total_adjusted.toFixed(2) }}</b>
        · 误差 <b>{{ allocResult.validation.error_pct.toFixed(2) }}%</b>
        {{ allocResult.validation.error_pct <= 1 ? "≤ 1%" : "⚠ 大于 1%" }}
      </div>

      <div class="allocator-actions" style="margin-top: 12px">
        <div style="flex: 1" />
        <button
          class="btn"
          :disabled="writingBack"
          @click="onWriteBack"
        >
          {{ writingBack ? "写回中…" : "↩ 写回 FP 表" }}
        </button>
      </div>

      <div v-if="writeBackBanner" class="banner banner-green" style="margin-top: 12px">
        ✓ {{ writeBackBanner }}
      </div>
    </template>
  </div>
</template>

<style scoped>
.allocator-panel { padding: 20px; margin-top: 16px; }
.allocator-head { margin-bottom: 14px; }
.allocator-drafts { margin-bottom: 12px; }
.allocator-drafts .field-input { height: 30px; font-size: 12px; }
.allocator-actions { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
</style>
