<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { functionsApi, type FunctionPoint, type FpCategory, type FpComplexity } from "@/api/functions";

const props = defineProps<{
  open: boolean;
  projectId: string;
  editing?: FunctionPoint | null;
  measurementMethod?: string;
}>();

const emit = defineEmits<{ "update:open": [v: boolean]; saved: [] }>();

// IFPUG GB/T 42449 标准表：category × complexity → UFP
const UFP_TABLE: Record<FpCategory, Record<FpComplexity, number>> = {
  EI:  { low: 3, average: 4, high: 6 },
  EO:  { low: 4, average: 5, high: 7 },
  EQ:  { low: 3, average: 4, high: 6 },
  ILF: { low: 7, average: 10, high: 15 },
  EIF: { low: 5, average: 7, high: 10 },
};

// IFPUG GB/T 42449 复杂度查表（与 server/app/core/ifpug.py 对齐）
const COMPLEXITY_MATRIX: FpComplexity[][] = [
  ["low", "low", "average"],
  ["low", "average", "high"],
  ["average", "high", "high"],
];

function retBand(ret: number): number {
  return ret <= 1 ? 0 : ret <= 5 ? 1 : 2;
}
function dataDetBand(det: number): number {
  return det <= 19 ? 0 : det <= 50 ? 1 : 2;
}
function ftrBandEi(ftr: number): number {
  return ftr <= 1 ? 0 : ftr === 2 ? 1 : 2;
}
function ftrBandEoEq(ftr: number): number {
  return ftr <= 1 ? 0 : ftr <= 3 ? 1 : 2;
}
function eiDetBand(det: number): number {
  return det <= 4 ? 0 : det <= 15 ? 1 : 2;
}
function eoEqDetBand(det: number): number {
  return det <= 5 ? 0 : det <= 19 ? 1 : 2;
}

function classifyComplexity(
  cat: FpCategory,
  det: number | null,
  ret: number | null,
  ftr: number | null,
): FpComplexity {
  if (cat === "ILF" || cat === "EIF") {
    if (det === null || ret === null) return "average";
    return COMPLEXITY_MATRIX[retBand(ret)][dataDetBand(det)];
  }
  if (det === null || ftr === null) return "average";
  if (cat === "EI") return COMPLEXITY_MATRIX[ftrBandEi(ftr)][eiDetBand(det)];
  return COMPLEXITY_MATRIX[ftrBandEoEq(ftr)][eoEqDetBand(det)]; // EO | EQ
}

const ALL_CATEGORIES: FpCategory[] = ["EI", "EO", "EQ", "ILF", "EIF"];
const INDICATIVE_CATEGORIES: FpCategory[] = ["ILF", "EIF"];

// --- measurement method derived flags ---
// Default undefined measurementMethod to "nesma_estimated" per spec.
const effectiveMethod = computed(() => props.measurementMethod ?? "nesma_estimated");
const isIfpugStyle = computed(() =>
  effectiveMethod.value === "ifpug" || effectiveMethod.value === "nesma_detailed",
);
const isNesmaEstimated = computed(() => effectiveMethod.value === "nesma_estimated");
const isNesmaIndicative = computed(() => effectiveMethod.value === "nesma_indicative");
const isCosmic = computed(() => effectiveMethod.value === "cosmic");

const effectiveCategories = computed<FpCategory[]>(() =>
  isNesmaIndicative.value ? INDICATIVE_CATEGORIES : ALL_CATEGORIES,
);

// --- form refs ---
const name = ref("");
const description = ref("");
const subsystem = ref("");
const l1_module = ref("");
const l2_module = ref("");
const category = ref<FpCategory>("EI");
const det = ref<number | null>(null);
const ret = ref<number | null>(null);
const ftr = ref<number | null>(null);

// COSMIC data movement counts
const cosmicEntry = ref<number | null>(null);
const cosmicExit = ref<number | null>(null);
const cosmicRead = ref<number | null>(null);
const cosmicWrite = ref<number | null>(null);

const submitting = ref(false);
const errorMsg = ref("");
const validationMsg = ref("");

// Guard: prevents the category watch from clearing det/ret/ftr during prefillForm
let suppressCategoryReset = false;

watch(category, () => {
  if (suppressCategoryReset) return;
  det.value = null;
  ret.value = null;
  ftr.value = null;
});

// When method switches to nesma_indicative and current category is not ILF/EIF, reset to ILF
watch(isNesmaIndicative, (v) => {
  if (v && !INDICATIVE_CATEGORIES.includes(category.value)) {
    category.value = "ILF";
  }
});

const complexity = computed<FpComplexity>(() => {
  if (isNesmaEstimated.value) return "average";
  return classifyComplexity(category.value, det.value, ret.value, ftr.value);
});

const computedUfp = computed<number>(() => UFP_TABLE[category.value][complexity.value]);

const cosmicCfpTotal = computed<number>(() =>
  (cosmicEntry.value ?? 0) +
  (cosmicExit.value ?? 0) +
  (cosmicRead.value ?? 0) +
  (cosmicWrite.value ?? 0),
);

function resetForm(): void {
  name.value = "";
  description.value = "";
  subsystem.value = "";
  l1_module.value = "";
  l2_module.value = "";
  category.value = isNesmaIndicative.value ? "ILF" : "EI";
  det.value = null;
  ret.value = null;
  ftr.value = null;
  cosmicEntry.value = null;
  cosmicExit.value = null;
  cosmicRead.value = null;
  cosmicWrite.value = null;
  errorMsg.value = "";
  validationMsg.value = "";
}

function prefillForm(fp: FunctionPoint): void {
  suppressCategoryReset = true;
  name.value = fp.name ?? "";
  description.value = fp.description ?? "";
  subsystem.value = fp.subsystem ?? "";
  l1_module.value = fp.l1_module ?? "";
  l2_module.value = fp.l2_module ?? "";
  category.value = fp.category;
  det.value = fp.det ?? null;
  ret.value = fp.ret ?? null;
  ftr.value = fp.ftr ?? null;
  // COSMIC fields — stored in extended props (may not exist on older FPs)
  const fpAny = fp as FunctionPoint & {
    cosmic_entry?: number | null;
    cosmic_exit?: number | null;
    cosmic_read?: number | null;
    cosmic_write?: number | null;
  };
  cosmicEntry.value = fpAny.cosmic_entry ?? null;
  cosmicExit.value = fpAny.cosmic_exit ?? null;
  cosmicRead.value = fpAny.cosmic_read ?? null;
  cosmicWrite.value = fpAny.cosmic_write ?? null;
  errorMsg.value = "";
  validationMsg.value = "";
  suppressCategoryReset = false;
}

watch(
  () => props.open,
  (v) => {
    if (v) {
      if (props.editing) {
        prefillForm(props.editing);
      } else {
        resetForm();
      }
    }
  },
  { immediate: true },
);

function close(): void {
  emit("update:open", false);
}

async function onSubmit(): Promise<void> {
  validationMsg.value = "";
  errorMsg.value = "";

  if (!name.value.trim()) {
    validationMsg.value = "功能点名称必填";
    return;
  }

  let payload: Record<string, unknown>;

  if (isCosmic.value) {
    const cfp = cosmicCfpTotal.value;
    payload = {
      name: name.value.trim(),
      description: description.value.trim() || undefined,
      subsystem: subsystem.value.trim() || undefined,
      l1_module: l1_module.value.trim() || undefined,
      l2_module: l2_module.value.trim() || undefined,
      category: category.value,
      cosmic_entry: cosmicEntry.value ?? 0,
      cosmic_exit: cosmicExit.value ?? 0,
      cosmic_read: cosmicRead.value ?? 0,
      cosmic_write: cosmicWrite.value ?? 0,
      ufp: cfp,
      us: cfp,
      ...(props.editing ? {} : { source: "manual" }),
    };
  } else if (isNesmaEstimated.value || isNesmaIndicative.value) {
    const ufp = computedUfp.value;
    payload = {
      name: name.value.trim(),
      description: description.value.trim() || undefined,
      subsystem: subsystem.value.trim() || undefined,
      l1_module: l1_module.value.trim() || undefined,
      l2_module: l2_module.value.trim() || undefined,
      category: category.value,
      complexity: complexity.value,
      ufp,
      us: ufp,
      ...(props.editing ? {} : { source: "manual" }),
    };
  } else {
    // ifpug / nesma_detailed
    const ufp = computedUfp.value;
    payload = {
      name: name.value.trim(),
      description: description.value.trim() || undefined,
      subsystem: subsystem.value.trim() || undefined,
      l1_module: l1_module.value.trim() || undefined,
      l2_module: l2_module.value.trim() || undefined,
      category: category.value,
      complexity: complexity.value,
      det: det.value ?? undefined,
      ret: ret.value ?? undefined,
      ftr: ftr.value ?? undefined,
      ufp,
      us: ufp,
      ...(props.editing ? {} : { source: "manual" }),
    };
  }

  submitting.value = true;
  try {
    if (props.editing) {
      await functionsApi.patch(props.projectId, props.editing.id, payload as Partial<FunctionPoint>);
    } else {
      await functionsApi.create(props.projectId, payload as Partial<FunctionPoint>);
    }
    emit("saved");
    close();
  } catch (e: unknown) {
    errorMsg.value = e instanceof Error ? e.message : "保存失败，请重试";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div v-if="open" class="modal-backdrop" @click.self="close">
    <div class="card fp-form-panel" role="dialog" :aria-label="editing ? '编辑功能点' : '新建功能点'">
      <div class="panel-head">
        <div class="section-title">{{ editing ? "编辑功能点" : "新建功能点" }}</div>
        <button type="button" class="btn btn-ghost btn-sm" @click="close">关闭</button>
      </div>

      <div v-if="errorMsg" class="banner banner-amber" style="margin-top: 12px">{{ errorMsg }}</div>

      <form class="fp-form" @submit.prevent="onSubmit">
        <div class="form-group">
          <label for="fp-name" class="form-label">功能点名称 <span class="required">*</span></label>
          <input
            id="fp-name"
            v-model="name"
            type="text"
            class="form-input"
            placeholder="请输入功能点名称"
            autocomplete="off"
            data-testid="input-name"
          >
          <p v-if="validationMsg" class="form-error">{{ validationMsg }}</p>
        </div>

        <div class="form-group">
          <label for="fp-desc" class="form-label">描述</label>
          <textarea
            id="fp-desc"
            v-model="description"
            class="form-input form-textarea"
            rows="3"
            placeholder="功能点描述（选填）"
          />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="fp-subsystem" class="form-label">子系统</label>
            <input
              id="fp-subsystem"
              v-model="subsystem"
              type="text"
              class="form-input"
              placeholder="子系统（选填）"
              autocomplete="off"
            >
          </div>
          <div class="form-group">
            <label for="fp-l1" class="form-label">一级模块</label>
            <input
              id="fp-l1"
              v-model="l1_module"
              type="text"
              class="form-input"
              placeholder="一级模块（选填）"
              autocomplete="off"
            >
          </div>
          <div class="form-group">
            <label for="fp-l2" class="form-label">二级模块</label>
            <input
              id="fp-l2"
              v-model="l2_module"
              type="text"
              class="form-input"
              placeholder="二级模块（选填）"
              autocomplete="off"
            >
          </div>
        </div>

        <!-- category: filtered by method for nesma_indicative -->
        <div class="form-row">
          <div class="form-group">
            <label for="fp-category" class="form-label">类别</label>
            <select id="fp-category" v-model="category" class="form-input form-select">
              <option
                v-for="cat in effectiveCategories"
                :key="cat"
                :value="cat"
                data-testid="category-option"
              >{{ cat }}</option>
            </select>
          </div>

          <!-- IFPUG / nesma_detailed: DET + RET/FTR -->
          <template v-if="isIfpugStyle">
            <div class="form-group">
              <label for="fp-det" class="form-label">DET（数据元素数）</label>
              <input
                id="fp-det"
                v-model.number="det"
                type="number"
                min="0"
                class="form-input"
                placeholder="字段数"
                data-testid="input-det"
              >
            </div>
            <!-- RET visible for data functions (ILF/EIF); FTR visible for transaction functions -->
            <div class="form-group" v-show="category === 'ILF' || category === 'EIF'">
              <label for="fp-ret" class="form-label">RET（记录元素数）</label>
              <input
                id="fp-ret"
                v-model.number="ret"
                type="number"
                min="0"
                class="form-input"
                placeholder="记录类型数"
                data-testid="input-ret"
              >
            </div>
            <div class="form-group" v-show="category !== 'ILF' && category !== 'EIF'">
              <label for="fp-ftr" class="form-label">FTR（引用文件数）</label>
              <input
                id="fp-ftr"
                v-model.number="ftr"
                type="number"
                min="0"
                class="form-input"
                placeholder="引用文件数"
                data-testid="input-ftr"
              >
            </div>
          </template>
        </div>

        <!-- COSMIC: 4 data movement inputs -->
        <template v-if="isCosmic">
          <div class="form-row">
            <div class="form-group">
              <label for="fp-cosmic-entry" class="form-label">入口（Entry）</label>
              <input
                id="fp-cosmic-entry"
                v-model.number="cosmicEntry"
                type="number"
                min="0"
                class="form-input"
                placeholder="入口移动数"
                data-testid="input-cosmic-entry"
              >
            </div>
            <div class="form-group">
              <label for="fp-cosmic-exit" class="form-label">出口（Exit）</label>
              <input
                id="fp-cosmic-exit"
                v-model.number="cosmicExit"
                type="number"
                min="0"
                class="form-input"
                placeholder="出口移动数"
                data-testid="input-cosmic-exit"
              >
            </div>
            <div class="form-group">
              <label for="fp-cosmic-read" class="form-label">读（Read）</label>
              <input
                id="fp-cosmic-read"
                v-model.number="cosmicRead"
                type="number"
                min="0"
                class="form-input"
                placeholder="读移动数"
                data-testid="input-cosmic-read"
              >
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="fp-cosmic-write" class="form-label">写（Write）</label>
              <input
                id="fp-cosmic-write"
                v-model.number="cosmicWrite"
                type="number"
                min="0"
                class="form-input"
                placeholder="写移动数"
                data-testid="input-cosmic-write"
              >
            </div>
            <div class="form-group">
              <span class="form-label">CFP（自动汇总）</span>
              <div class="ufp-display">
                <span data-testid="cfp-total" class="ufp-value">{{ cosmicCfpTotal }}</span>
                <span class="ufp-hint muted">入口 + 出口 + 读 + 写</span>
              </div>
            </div>
          </div>
        </template>

        <!-- nesma_estimated: complexity fixed to average (中) -->
        <div v-else-if="isNesmaEstimated" class="form-row">
          <div class="form-group">
            <span class="form-label">复杂度（估算级固定）</span>
            <div class="ufp-display">
              <span data-testid="fp-complexity-auto" class="ufp-value">中</span>
              <span class="ufp-hint muted">NESMA 估算级固定为中等复杂度</span>
            </div>
          </div>
          <div class="form-group">
            <span class="form-label">UFP（自动）</span>
            <div class="ufp-display">
              <span data-testid="fp-ufp-auto" class="ufp-value">{{ computedUfp }}</span>
              <span class="ufp-hint muted">按类别 × 中等复杂度查表</span>
            </div>
          </div>
        </div>

        <!-- ifpug / nesma_detailed / nesma_indicative: complexity auto display -->
        <div v-else class="form-row">
          <div class="form-group">
            <span class="form-label">复杂度（IFPUG 自动）</span>
            <div class="ufp-display">
              <span data-testid="fp-complexity-auto" class="ufp-value">
                {{ complexity === 'low' ? '低' : complexity === 'high' ? '高' : '中' }}
              </span>
              <span class="ufp-hint muted">按 GB/T 42449 查表</span>
            </div>
          </div>
          <div class="form-group">
            <span class="form-label">UFP（自动）</span>
            <div class="ufp-display">
              <span data-testid="fp-ufp-auto" class="ufp-value">{{ computedUfp }}</span>
              <span class="ufp-hint muted">按 IFPUG 标准表自动计算</span>
            </div>
          </div>
        </div>

        <div class="form-actions">
          <button type="button" class="btn btn-ghost" @click="close">取消</button>
          <button type="submit" class="btn btn-primary" :disabled="submitting">
            {{ submitting ? "保存中…" : (editing ? "保存修改" : "创建功能点") }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: grid;
  place-items: center;
  z-index: 1000;
}

.fp-form-panel {
  width: 640px;
  max-width: 94vw;
  max-height: 90vh;
  overflow-y: auto;
  padding: 24px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.fp-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-label {
  font-size: var(--font-size-sm, 13px);
  font-weight: 500;
  color: var(--color-text, #1e293b);
}

.required {
  color: var(--red, #dc2626);
}

.form-input {
  padding: 8px 10px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius, 6px);
  font-size: var(--font-size-sm, 13px);
  background: var(--color-bg-elevated, #fff);
  color: var(--color-text, #1e293b);
  transition: border-color 0.15s;
  outline: none;
}

.form-input:focus {
  border-color: var(--color-primary, #165dff);
  box-shadow: 0 0 0 2px rgba(22, 93, 255, 0.12);
}

.form-textarea {
  resize: vertical;
  min-height: 72px;
}

.form-select {
  cursor: pointer;
}

.form-error {
  margin: 0;
  font-size: 12px;
  color: var(--red, #dc2626);
}

.ufp-display {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius, 6px);
  background: var(--color-bg-hover, #f8fafc);
  min-height: 38px;
}

.ufp-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-primary, #165dff);
  min-width: 24px;
}

.ufp-hint {
  font-size: 11px;
  color: var(--color-text-muted, #94a3b8);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 4px;
}

.muted {
  color: var(--color-text-muted, #94a3b8);
}
</style>
