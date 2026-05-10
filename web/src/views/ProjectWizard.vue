<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useProjectsStore } from "@/stores/projects";
import { paramsApi, type EffectiveParams } from "@/api/params";
import type {
  Project,
  ProjectMode,
  ProjectPhase,
  ProjectType,
} from "@/api/projects";

const BASIS_DATA_VER = "CSBMK®-202510";

const router = useRouter();
const store = useProjectsStore();

interface FormState {
  mode: ProjectMode;
  name: string;
  city: string;
  industry: string;
  phase: ProjectPhase;
  project_type: ProjectType;
  target_total: number;
  alpha: number;
  client: string;
  evaluator: string;
  include_ops: boolean;
  factors_dev: Record<string, string>;
  factors_ops: Record<string, string>;
}

const form = reactive<FormState>({
  mode: "forward",
  name: "",
  city: "北京",
  industry: "电子政务",
  phase: "bidding",
  project_type: "dev_only",
  target_total: 0,
  alpha: 0.7,
  client: "",
  evaluator: "",
  include_ops: false,
  factors_dev: {},
  factors_ops: {},
});

const currentStep = ref(1);
const totalSteps = 7;
const STEP_LABELS = [
  "基础信息",
  "项目类型",
  "阶段",
  "正/反向",
  "开发因子",
  "运维因子",
  "确认",
];

const submitting = ref(false);
const errorMsg = ref<string | null>(null);

const CITIES = [
  "北京", "天津", "上海", "重庆", "石家庄", "太原", "呼和浩特", "西安", "成都",
  "昆明", "武汉", "长沙", "合肥", "长春", "沈阳", "大连", "哈尔滨", "济南",
  "青岛", "郑州", "南京", "苏州", "杭州", "宁波", "福州", "厦门", "广州",
  "深圳", "南昌", "南宁", "海口", "兰州", "贵阳", "银川", "乌鲁木齐", "拉萨", "西宁",
];

const INDUSTRIES = ["全行业", "电子政务", "金融", "电信", "制造", "能源", "交通"];

const canAdvance = computed<boolean>(() => {
  if (currentStep.value === 1) return form.name.trim().length > 0;
  if (currentStep.value === 4) {
    return form.mode === "forward" || form.target_total > 0;
  }
  return true;
});

function next(): void {
  if (canAdvance.value && currentStep.value < totalSteps) currentStep.value += 1;
}

function back(): void {
  if (currentStep.value > 1) currentStep.value -= 1;
}

// 拉取 effective 参数（用于后续 T15 PhaseCfPreview / T17 因子默认值展示）。
// 失败时静默 — 后续 step 自行兜底或显示默认值。
const effectiveParams = ref<EffectiveParams | null>(null);
onMounted(async () => {
  try {
    // 新建项目场景：尚无 projectId。后端 /api/params/global 提供等价的全局有效参数。
    const resp = await paramsApi.global();
    effectiveParams.value = resp ?? null;
  } catch {
    // 静默兜底
  }
});

async function submit(): Promise<void> {
  submitting.value = true;
  errorMsg.value = null;
  try {
    const payload: Partial<Project> & { mode: ProjectMode } = {
      name: form.name,
      mode: form.mode,
      city: form.city,
      industry: form.industry,
      phase: form.phase,
      project_type: form.project_type,
      basis_data_ver: BASIS_DATA_VER,
      alpha_dev: form.alpha,
      target_cost:
        form.mode === "reverse" ? form.target_total : undefined,
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
      <span class="text-muted step-indicator">第 {{ currentStep }} / {{ totalSteps }} 步</span>
    </header>

    <ol class="wizard-steps">
      <li
        v-for="(label, idx) in STEP_LABELS"
        :key="idx"
        class="step"
        data-testid="wizard-step"
        :data-active="idx + 1 === currentStep"
        :data-done="idx + 1 < currentStep"
      >
        <span class="num">{{ idx + 1 }}</span>
        <span class="label">{{ label }}</span>
      </li>
    </ol>

    <form
      class="card wizard-card"
      @submit.prevent
    >
      <fieldset v-if="currentStep === 1">
        <legend>基础信息</legend>
        <label class="field">
          <span class="field-label">项目名 *</span>
          <input
            v-model="form.name"
            name="name"
            type="text"
            required
            maxlength="120"
          >
        </label>
        <label class="field">
          <span class="field-label">城市 *</span>
          <select v-model="form.city">
            <option
              v-for="c in CITIES"
              :key="c"
              :value="c"
            >{{ c }}</option>
          </select>
        </label>
        <label class="field">
          <span class="field-label">行业 *</span>
          <select v-model="form.industry">
            <option
              v-for="i in INDUSTRIES"
              :key="i"
              :value="i"
            >{{ i }}</option>
          </select>
        </label>
        <label class="field">
          <span class="field-label">客户（可选）</span>
          <input
            v-model="form.client"
            name="client"
            type="text"
            maxlength="80"
          >
        </label>
        <label class="field">
          <span class="field-label">评估方（可选）</span>
          <input
            v-model="form.evaluator"
            name="evaluator"
            type="text"
            maxlength="80"
          >
        </label>
      </fieldset>

      <fieldset v-else-if="currentStep === 2">
        <legend>项目类型</legend>
        <p class="placeholder">
          将在 T14 填充：dev_only / ops_only / dev_and_ops 选择
        </p>
      </fieldset>

      <fieldset v-else-if="currentStep === 3">
        <legend>阶段</legend>
        <p class="placeholder">
          将在 T15 填充：评估阶段 + PhaseCfPreview
        </p>
      </fieldset>

      <fieldset v-else-if="currentStep === 4">
        <legend>正向 / 反向</legend>
        <p class="placeholder">
          将在 T16 填充：mode + 反向模式 target_total
        </p>
      </fieldset>

      <fieldset v-else-if="currentStep === 5">
        <legend>开发因子</legend>
        <p class="placeholder">
          将在 T17 填充：factors_dev 选择
        </p>
      </fieldset>

      <fieldset v-else-if="currentStep === 6">
        <legend>运维因子</legend>
        <p class="placeholder">
          将在 T17 填充：factors_ops 选择（仅 include_ops 时显示）
        </p>
      </fieldset>

      <fieldset v-else-if="currentStep === 7">
        <legend>确认</legend>
        <p class="placeholder">
          将在 T18 填充：摘要 + 创建
        </p>
        <pre class="confirm-summary">{{ JSON.stringify(form, null, 2) }}</pre>
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
          :disabled="currentStep === 1 || submitting"
          @click="back"
        >
          上一步
        </button>
        <button
          v-if="currentStep < totalSteps"
          type="button"
          class="btn btn-primary"
          data-test="wizard-next"
          :disabled="!canAdvance"
          @click="next"
        >
          下一步
        </button>
        <button
          v-else
          type="button"
          class="btn btn-primary"
          :disabled="submitting"
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
.wizard-steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}
.step {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  background: var(--color-bg);
  transition: all var(--duration-fast) var(--ease-out);
}
.step[data-active="true"] {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-weight: 600;
}
.step[data-done="true"] {
  border-color: var(--color-success, var(--color-primary));
  color: var(--color-success, var(--color-primary));
}
.step .num {
  display: inline-flex;
  width: 1.5em;
  height: 1.5em;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  background: var(--color-bg-alt, var(--color-bg));
  font-weight: 600;
}
.step[data-active="true"] .num {
  background: var(--color-primary);
  color: var(--color-bg);
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
.placeholder {
  color: var(--color-text-muted);
  font-style: italic;
  background: var(--color-bg);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  margin: 0;
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
