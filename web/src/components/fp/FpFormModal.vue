<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { functionsApi, type FunctionPoint, type FpCategory, type FpComplexity } from "@/api/functions";

const props = defineProps<{
  open: boolean;
  projectId: string;
  editing?: FunctionPoint | null;
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

const CATEGORIES: FpCategory[] = ["EI", "EO", "EQ", "ILF", "EIF"];

const name = ref("");
const description = ref("");
const subsystem = ref("");
const l1_module = ref("");
const l2_module = ref("");
const category = ref<FpCategory>("EI");
const det = ref<number | null>(null);
const ret = ref<number | null>(null);
const ftr = ref<number | null>(null);

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

const complexity = computed<FpComplexity>(() =>
  classifyComplexity(category.value, det.value, ret.value, ftr.value),
);

const computedUfp = computed<number>(() => UFP_TABLE[category.value][complexity.value]);

function resetForm(): void {
  name.value = "";
  description.value = "";
  subsystem.value = "";
  l1_module.value = "";
  l2_module.value = "";
  category.value = "EI";
  det.value = null;
  ret.value = null;
  ftr.value = null;
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

  const ufp = computedUfp.value;
  const payload: Partial<FunctionPoint> = {
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

  submitting.value = true;
  try {
    if (props.editing) {
      await functionsApi.patch(props.projectId, props.editing.id, payload);
    } else {
      await functionsApi.create(props.projectId, payload);
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

        <div class="form-row">
          <div class="form-group">
            <label for="fp-category" class="form-label">类别</label>
            <select id="fp-category" v-model="category" class="form-input form-select">
              <option v-for="cat in CATEGORIES" :key="cat" :value="cat">{{ cat }}</option>
            </select>
          </div>
          <div class="form-group">
            <label for="fp-det" class="form-label">DET（数据元素数）</label>
            <input id="fp-det" v-model.number="det" type="number" min="0"
                   class="form-input" placeholder="字段数">
          </div>
          <div class="form-group" v-if="category === 'ILF' || category === 'EIF'">
            <label for="fp-ret" class="form-label">RET（记录元素数）</label>
            <input id="fp-ret" v-model.number="ret" type="number" min="0"
                   class="form-input" placeholder="记录类型数">
          </div>
          <div class="form-group" v-else>
            <label for="fp-ftr" class="form-label">FTR（引用文件数）</label>
            <input id="fp-ftr" v-model.number="ftr" type="number" min="0"
                   class="form-input" placeholder="引用文件数">
          </div>
        </div>

        <div class="form-row">
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
