<script setup lang="ts">
import { ref, computed } from "vue";
import { calcApi, type AllocateResult, type ReverseResult } from "@/api/calc";

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
}>();

const drafts = ref<DraftRow[]>([
  { name: "前端", weight: 1.0, locked: false, locked_us: 0 },
  { name: "后端", weight: 1.5, locked: false, locked_us: 0 },
]);
const allocResult = ref<AllocateResult | null>(null);
const allocating = ref(false);
const hint = ref<string>("");

function addRow() {
  drafts.value.push({ name: `模块 ${drafts.value.length + 1}`, weight: 1.0, locked: false, locked_us: 0 });
}
function removeRow(idx: number) {
  drafts.value.splice(idx, 1);
}

const canAllocate = computed(() => drafts.value.length > 0 && drafts.value.every((d) => d.name.trim()));

async function onGenerate() {
  if (!canAllocate.value) {
    hint.value = "请确保所有模块都填写名称。";
    return;
  }
  const band = props.reverseResult.recommended_band ?? "P50";
  const targetUs = props.reverseResult.scale_adjusted_bands?.[band];
  if (!targetUs || targetUs <= 0) {
    hint.value = "反向结果无可用推荐档 FP，请重算 reverse。";
    return;
  }
  allocating.value = true;
  hint.value = "";
  try {
    const res = await calcApi.allocate({
      project_id: props.projectId,
      target_us: targetUs,
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
</script>

<template>
  <div class="card allocator-panel">
    <div class="allocator-head">
      <div class="section-title">AI 模块分摊</div>
      <div class="muted" style="font-size: 12px">权重决定模块 FP 占比；锁定模块按 locked_us 固定值不参与分摊</div>
    </div>

    <table class="table allocator-drafts">
      <thead>
        <tr>
          <th>模块名</th>
          <th style="width: 200px">权重</th>
          <th style="width: 110px">锁定 FP</th>
          <th style="width: 40px"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(d, idx) in drafts" :key="idx">
          <td><input class="field-input" v-model="d.name" /></td>
          <td>
            <input type="range" min="0.5" max="3" step="0.1" v-model.number="d.weight" style="width: 100%" />
            <span class="mono muted" style="font-size: 11px">{{ d.weight.toFixed(1) }}</span>
          </td>
          <td>
            <input class="field-input mono" type="number" min="0" step="0.5" v-model.number="d.locked_us" placeholder="0" />
          </td>
          <td>
            <button class="btn btn-sm btn-ghost" @click="removeRow(idx)" aria-label="删除">✕</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div class="allocator-actions">
      <button class="btn btn-ghost" @click="addRow">+ 新增模块</button>
      <div style="flex: 1" />
      <button class="btn btn-primary" :disabled="!canAllocate || allocating" @click="onGenerate">
        {{ allocating ? "生成中…" : "✨ 生成分摊" }}
      </button>
    </div>

    <div v-if="hint" class="banner banner-amber" style="margin-top: 12px">{{ hint }}</div>

    <template v-if="allocResult">
      <div class="section-head" style="margin-top: 20px">
        <div class="section-title">分摊结果</div>
      </div>
      <table class="table">
        <thead>
          <tr>
            <th>模块</th>
            <th style="text-align: right">分配 FP (US)</th>
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
        · 反算总 US <b class="mono">{{ allocResult.validation.recalc_total_us.toFixed(2) }}</b>
        · 调整后 <b class="mono">{{ allocResult.validation.recalc_total_adjusted.toFixed(2) }}</b>
        · 误差 <b>{{ allocResult.validation.error_pct.toFixed(2) }}%</b>
        {{ allocResult.validation.error_pct <= 1 ? "≤ 1%" : "⚠ 大于 1%" }}
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
