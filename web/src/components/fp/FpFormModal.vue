<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { functionsApi, type FunctionPoint, type FpCategory, type FpComplexity } from "@/api/functions";

const props = defineProps<{
  open: boolean;
  projectId: string;
  editing?: FunctionPoint | null;
}>();

const emit = defineEmits<{ "update:open": [v: boolean]; saved: [] }>();

// NESMA 标准表：category × complexity → UFP
const UFP_TABLE: Record<FpCategory, Record<FpComplexity, number>> = {
  EI:  { low: 3, average: 4, high: 6 },
  EO:  { low: 4, average: 5, high: 7 },
  EQ:  { low: 3, average: 4, high: 6 },
  ILF: { low: 7, average: 10, high: 15 },
  EIF: { low: 5, average: 7, high: 10 },
};

const CATEGORIES: FpCategory[] = ["EI", "EO", "EQ", "ILF", "EIF"];
const COMPLEXITY_OPTIONS: { value: FpComplexity; label: string }[] = [
  { value: "low", label: "低" },
  { value: "average", label: "中" },
  { value: "high", label: "高" },
];
const name = ref("");
const description = ref("");
const subsystem = ref("");
const l1_module = ref("");
const l2_module = ref("");
const category = ref<FpCategory>("EI");
const complexity = ref<FpComplexity>("low");

const submitting = ref(false);
const errorMsg = ref("");
const validationMsg = ref("");

const computedUfp = computed<number>(() => UFP_TABLE[category.value][complexity.value]);

function resetForm(): void {
  name.value = "";
  description.value = "";
  subsystem.value = "";
  l1_module.value = "";
  l2_module.value = "";
  category.value = "EI";
  complexity.value = "low";
  errorMsg.value = "";
  validationMsg.value = "";
}

function prefillForm(fp: FunctionPoint): void {
  name.value = fp.name ?? "";
  description.value = fp.description ?? "";
  subsystem.value = fp.subsystem ?? "";
  l1_module.value = fp.l1_module ?? "";
  l2_module.value = fp.l2_module ?? "";
  category.value = fp.category;
  complexity.value = fp.complexity;
  errorMsg.value = "";
  validationMsg.value = "";
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
            <label for="fp-complexity" class="form-label">复杂度</label>
            <select id="fp-complexity" v-model="complexity" class="form-input form-select">
              <option
                v-for="opt in COMPLEXITY_OPTIONS"
                :key="opt.value"
                :value="opt.value"
              >{{ opt.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">UFP（自动）</label>
            <div class="ufp-display">
              <span class="ufp-value">{{ computedUfp }}</span>
              <span class="ufp-hint muted">按 NESMA 标准表自动计算</span>
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
