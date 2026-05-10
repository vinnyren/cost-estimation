<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useProjectsStore } from "@/stores/projects";
import type {
  Project,
  ProjectMode,
  ProjectPhase,
  ProjectType,
} from "@/api/projects";

const BASIS_DATA_VER = "CSBMK®-202510";

const router = useRouter();
const store = useProjectsStore();

const step = ref(1);
const TOTAL_STEPS = 5;

const form = ref<{
  mode: ProjectMode | "";
  name: string;
  city: string;
  industry: string;
  phase: ProjectPhase;
  project_type: ProjectType;
  target_total: number;
  alpha: number;
}>({
  mode: "",
  name: "",
  city: "北京",
  industry: "电子政务",
  phase: "bidding",
  project_type: "dev_only",
  target_total: 0,
  alpha: 1.0,
});

const submitting = ref(false);
const errorMsg = ref<string | null>(null);

const CITIES = [
  "北京", "天津", "上海", "重庆", "石家庄", "太原", "呼和浩特", "西安", "成都",
  "昆明", "武汉", "长沙", "合肥", "长春", "沈阳", "大连", "哈尔滨", "济南",
  "青岛", "郑州", "南京", "苏州", "杭州", "宁波", "福州", "厦门", "广州",
  "深圳", "南昌", "南宁", "海口", "兰州", "贵阳", "银川", "乌鲁木齐", "拉萨", "西宁",
];

const INDUSTRIES = ["全行业", "电子政务", "金融", "电信", "制造", "能源", "交通"];
const STAGES: Array<{ value: ProjectPhase; label: string }> = [
  { value: "budget", label: "预算" },
  { value: "bidding", label: "招投标" },
  { value: "planning", label: "立项" },
  { value: "change", label: "变更" },
  { value: "settled", label: "结算" },
];

const canNext = computed(() => {
  if (step.value === 1) return !!form.value.mode;
  if (step.value === 2) return form.value.name.trim().length > 0;
  if (step.value === 3) return CITIES.includes(form.value.city) && INDUSTRIES.includes(form.value.industry);
  if (step.value === 4) return STAGES.some((s) => s.value === form.value.phase);
  if (step.value === 5) {
    if (form.value.mode === "reverse") return form.value.target_total > 0;
    return true;
  }
  return false;
});

function next(): void {
  if (canNext.value && step.value < TOTAL_STEPS) step.value += 1;
}

function back(): void {
  if (step.value > 1) step.value -= 1;
}

async function submit(): Promise<void> {
  if (form.value.mode === "") {
    errorMsg.value = "请选择评估模式";
    return;
  }
  submitting.value = true;
  errorMsg.value = null;
  try {
    const payload: Partial<Project> & { mode: ProjectMode } = {
      name: form.value.name,
      mode: form.value.mode,
      city: form.value.city,
      industry: form.value.industry,
      phase: form.value.phase,
      project_type: form.value.project_type,
      basis_data_ver: BASIS_DATA_VER,
      alpha_dev: form.value.alpha,
      target_cost:
        form.value.mode === "reverse" ? form.value.target_total : undefined,
    };
    const created = await store.create(payload);
    router.push({ name: "fp-editor", params: { id: created.id } });
  } catch (e: unknown) {
    errorMsg.value = e instanceof Error ? e.message : "创建失败";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section
    class="page"
    aria-labelledby="title"
  >
    <header class="page-header">
      <h1 id="title">
        新建项目
      </h1>
      <span class="text-muted step-indicator">第 {{ step }} / {{ TOTAL_STEPS }} 步</span>
    </header>
    <div class="progress-wrap">
      <progress
        :value="step"
        :max="TOTAL_STEPS"
      />
    </div>

    <form
      class="card wizard-card"
      @submit.prevent
    >
      <fieldset v-if="step === 1">
        <legend>选择评估模式</legend>
        <div class="radio-group">
          <label class="radio-row">
            <input
              v-model="form.mode"
              type="radio"
              value="forward"
            >
            <span>正向（已知功能点 → 估算造价）</span>
          </label>
          <label class="radio-row">
            <input
              v-model="form.mode"
              type="radio"
              value="reverse"
            >
            <span>反向（已知目标造价 → 反推功能点）</span>
          </label>
        </div>
      </fieldset>

      <fieldset v-else-if="step === 2">
        <legend>项目名称</legend>
        <label class="field">
          <span class="field-label">名称</span>
          <input
            v-model="form.name"
            type="text"
            required
          >
        </label>
      </fieldset>

      <fieldset v-else-if="step === 3">
        <legend>城市与行业</legend>
        <label class="field">
          <span class="field-label">城市</span>
          <select v-model="form.city">
            <option
              v-for="c in CITIES"
              :key="c"
              :value="c"
            >{{ c }}</option>
          </select>
        </label>
        <label class="field">
          <span class="field-label">行业</span>
          <select v-model="form.industry">
            <option
              v-for="i in INDUSTRIES"
              :key="i"
              :value="i"
            >{{ i }}</option>
          </select>
        </label>
      </fieldset>

      <fieldset v-else-if="step === 4">
        <legend>评估阶段</legend>
        <div class="radio-group">
          <label
            v-for="s in STAGES"
            :key="s.value"
            class="radio-row"
          >
            <input
              v-model="form.phase"
              type="radio"
              :value="s.value"
            >
            <span>{{ s.label }}</span>
          </label>
        </div>
      </fieldset>

      <fieldset v-else-if="step === 5">
        <legend>{{ form.mode === "reverse" ? "目标金额" : "确认信息" }}</legend>
        <template v-if="form.mode === 'reverse'">
          <label class="field">
            <span class="field-label">目标总造价（元）</span>
            <input
              v-model.number="form.target_total"
              type="number"
              min="0"
            >
          </label>
          <label class="field">
            <span class="field-label">α 调整系数</span>
            <input
              v-model.number="form.alpha"
              type="number"
              min="0"
              step="0.01"
            >
          </label>
        </template>
        <pre
          v-else
          class="confirm-summary"
        >{{ JSON.stringify(form, null, 2) }}</pre>
        <p
          v-if="errorMsg"
          role="alert"
          class="error"
        >
          {{ errorMsg }}
        </p>
      </fieldset>

      <div class="nav">
        <button
          type="button"
          class="btn"
          :disabled="step === 1 || submitting"
          @click="back"
        >
          上一步
        </button>
        <button
          v-if="step < TOTAL_STEPS"
          type="button"
          class="btn btn-primary"
          data-test="wizard-next"
          :disabled="!canNext"
          @click="next"
        >
          下一步
        </button>
        <button
          v-else
          type="button"
          class="btn btn-primary"
          :disabled="!canNext || submitting"
          @click="submit"
        >
          {{ submitting ? "创建中…" : "创建项目" }}
        </button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 720px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.page-header h1 {
  margin: 0;
}
.step-indicator {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}
.progress-wrap {
  width: 100%;
}
progress {
  width: 100%;
  height: 6px;
  border: none;
  border-radius: var(--radius-sm);
  overflow: hidden;
  appearance: none;
  background: var(--color-bg);
}
progress::-webkit-progress-bar {
  background: var(--color-bg);
  border-radius: var(--radius-sm);
}
progress::-webkit-progress-value {
  background: var(--color-primary);
  border-radius: var(--radius-sm);
  transition: width var(--duration-normal) var(--ease-out);
}
progress::-moz-progress-bar {
  background: var(--color-primary);
  border-radius: var(--radius-sm);
}
.wizard-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
fieldset {
  border: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
legend {
  font-weight: 600;
  color: var(--color-text-title);
  font-size: var(--font-size-md);
  padding: 0;
  margin-bottom: var(--space-2);
}
.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.field-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: 500;
}
.radio-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.radio-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}
.radio-row:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
}
.radio-row input[type="radio"] {
  accent-color: var(--color-primary);
  margin: 0;
  height: auto;
}
.confirm-summary {
  background: var(--color-bg);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  color: var(--color-text-body);
  margin: 0;
  overflow: auto;
  max-height: 240px;
}
.nav {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
}
.error {
  color: var(--color-danger);
  background: var(--color-danger-bg);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-danger);
  margin: 0;
  font-size: var(--font-size-sm);
}
</style>
