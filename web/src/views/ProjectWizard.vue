<script setup lang="ts">
/**
 * ProjectWizard — 新建项目向导（v2.0 7 步骨架）。
 *
 * v1.1 是 5 步；v2.0 拆出"项目类型 (T14)"和"阶段 (T15)"独立成步，并新增
 * step 5 / 6 的开发/运维因子配置（T17）。7 步:
 *   1 基础信息   2 项目类型   3 阶段   4 正/反向
 *   5 开发因子   6 运维因子（按 include_ops 跳过）   7 确认
 *
 * 关键 form 字段（v2 新增标 *）：
 *   - name / city / industry / phase / mode / target_total — v1 已有
 *   - project_type *, client *, evaluator *, alpha *,
 *     factors_dev *, factors_ops *, include_ops *
 *
 * Submit 把所有字段拼成 projectsApi.create payload；TS Project 接口未声明
 * factors_dev/ops（仅后端 schema 有），所以用 intersection 类型扩展。
 */
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
import AlphaSlider from "@/components/AlphaSlider.vue";
import PhaseCfPreview from "@/components/PhaseCfPreview.vue";
import FactorDropdown from "@/components/FactorDropdown.vue";

// 因子展示标签 — 与 ParamManager.vue 中的 FACTOR_LABELS 保持一致。
// 重复定义而非共享是有意为之：T17 完成时这两处独立演进；后续若有第三个使用方
// 再统一抽到 src/lib/factor-labels.ts。
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

interface NormalizedLevel {
  multiplier: number;
  description?: string;
}

/**
 * CSBMK®-202510 中 factors_dev / factors_ops 的 level value 是直接数字
 * (e.g. { app_type: { "业务处理": 1.0 } })。FactorDropdown 期望
 * { multiplier: number } 形态 — 这里做适配，与 ParamManager.normalizeLevels 一致。
 */
function normalizeLevels(
  rawLevels: Record<string, unknown>,
): Record<string, NormalizedLevel> {
  const out: Record<string, NormalizedLevel> = {};
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

/**
 * 给定一组用户选择（factor → levelKey）与 effective 中对应组的原始定义，
 * 按链相乘得到总因子。空选 / 未匹配的因子按 ×1.00 计算。
 */
function chainMultiply(
  selections: Record<string, string>,
  defs: Record<string, Record<string, unknown>>,
): number {
  let f = 1.0;
  for (const [factorName, levelKey] of Object.entries(selections)) {
    if (!levelKey) continue;
    const raw = defs?.[factorName]?.[levelKey];
    const m =
      typeof raw === "number"
        ? raw
        : raw && typeof raw === "object"
          ? (raw as { multiplier?: number }).multiplier
          : undefined;
    if (typeof m === "number") f *= m;
  }
  return f;
}

const PROJECT_TYPE_LABELS: Record<ProjectType, string> = {
  dev_only: "仅开发",
  ops_only: "仅运维",
  dev_and_ops: "开发 + 运维",
};
const PROJECT_TYPES = ["dev_only", "ops_only", "dev_and_ops"] as const;

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

// 步进闸门：step 1 必须填项目名；step 4 反向模式必须给非零目标成本
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

// project_type 改变时联动 include_ops / alpha — dev_only 时 α 强制 1.0
// 等价于"纯开发"；其余两类都包含运维。后端 schema 也有同等约束。
function onProjectTypeChange(): void {
  if (form.project_type === "ops_only") {
    form.include_ops = true;
  } else if (form.project_type === "dev_and_ops") {
    form.include_ops = true;
  } else if (form.project_type === "dev_only") {
    form.include_ops = false;
    form.alpha = 1.0;
  }
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

// 实时 chain 预览：用户在 step 5 / 6 选 dropdown 时即时显示乘积。
const devFactorPreview = computed<number>(() =>
  chainMultiply(
    form.factors_dev,
    (effectiveParams.value?.factors_dev ?? {}) as Record<string, Record<string, unknown>>,
  ),
);
const opsFactorPreview = computed<number>(() =>
  chainMultiply(
    form.factors_ops,
    (effectiveParams.value?.factors_ops ?? {}) as Record<string, Record<string, unknown>>,
  ),
);

function hasAnyFactor(obj: Record<string, string>): boolean {
  return Object.values(obj).some((v) => v && v.length > 0);
}

async function submit(): Promise<void> {
  submitting.value = true;
  errorMsg.value = null;
  try {
    // v2.0 payload: project core + 调整因子。Partial<Project> 覆盖核心字段；
    // factors_dev/factors_ops 在 TS Project 接口上未声明（后端 schema
    // 在 server/app/schemas/project.py 已有），这里用 intersection 显式扩展。
    const payload: Partial<Project> &
      { mode: ProjectMode } &
      {
        factors_dev?: Record<string, string>;
        factors_ops?: Record<string, string>;
      } = {
      name: form.name,
      project_type: form.project_type,
      phase: form.phase,
      city: form.city,
      industry: form.industry,
      client: form.client || undefined,
      evaluator: form.evaluator || undefined,
      mode: form.mode,
      target_cost:
        form.mode === "reverse" ? form.target_total : undefined,
      include_ops: form.include_ops,
      alpha_dev: form.alpha,
      basis_data_ver: BASIS_DATA_VER,
      factors_dev: hasAnyFactor(form.factors_dev)
        ? { ...form.factors_dev }
        : undefined,
      factors_ops:
        form.include_ops && hasAnyFactor(form.factors_ops)
          ? { ...form.factors_ops }
          : undefined,
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
        <div
          class="radio-group"
          role="radiogroup"
          aria-label="项目类型"
        >
          <label
            v-for="t in PROJECT_TYPES"
            :key="t"
            class="radio"
          >
            <input
              type="radio"
              name="project_type"
              :value="t"
              :checked="form.project_type === t"
              @change="(form.project_type = t), onProjectTypeChange()"
            >
            <span>{{ PROJECT_TYPE_LABELS[t] }}</span>
          </label>
        </div>
        <label
          v-if="form.project_type !== 'ops_only'"
          class="checkbox"
        >
          <input
            v-model="form.include_ops"
            type="checkbox"
            name="include_ops"
            :disabled="form.project_type === 'dev_and_ops'"
          >
          <span>包含运维成本</span>
        </label>
        <AlphaSlider
          v-if="form.project_type === 'dev_and_ops'"
          v-model="form.alpha"
        />
      </fieldset>

      <fieldset v-else-if="currentStep === 3">
        <legend>项目阶段</legend>
        <PhaseCfPreview
          :phase="form.phase"
          :cf="effectiveParams?.cf ?? {}"
          @update:phase="(v: string) => (form.phase = v as ProjectPhase)"
        />
      </fieldset>

      <fieldset v-else-if="currentStep === 4">
        <legend>计算模式</legend>
        <div
          class="radio-group"
          role="radiogroup"
          aria-label="计算模式"
        >
          <label class="radio">
            <input
              v-model="form.mode"
              type="radio"
              name="mode"
              value="forward"
            >
            <span>正向 — 已有功能点 → 估算成本</span>
          </label>
          <label class="radio">
            <input
              v-model="form.mode"
              type="radio"
              name="mode"
              value="reverse"
            >
            <span>反向 — 已有目标成本 → 推算功能点</span>
          </label>
        </div>
        <label
          v-if="form.mode === 'reverse'"
          class="field"
        >
          <span class="field-label">目标总成本（元） *</span>
          <input
            v-model.number="form.target_total"
            name="target_total"
            type="number"
            min="1"
            required
          >
        </label>
      </fieldset>

      <fieldset v-else-if="currentStep === 5">
        <legend>开发调整因子</legend>
        <p class="hint">
          不填的因子按 ×1.00 计算（不影响成本）。
        </p>
        <FactorDropdown
          v-for="(levels, key) in (effectiveParams?.factors_dev ?? {})"
          :key="String(key)"
          :factor="{
            name: String(key),
            label: FACTOR_LABELS[String(key)] ?? String(key),
            levels: normalizeLevels(levels as Record<string, unknown>),
          }"
          :model-value="form.factors_dev[String(key)]"
          @update:model-value="(v: string) => (form.factors_dev[String(key)] = v)"
        />
        <div
          class="factor-chain-preview"
          data-testid="dev-factor-preview"
        >
          实时 dev_factor 链 = <strong>{{ devFactorPreview.toFixed(2) }}</strong>
        </div>
      </fieldset>

      <fieldset v-else-if="currentStep === 6 && form.include_ops">
        <legend>运维调整因子</legend>
        <p class="hint">
          不填的因子按 ×1.00 计算（不影响成本）。
        </p>
        <FactorDropdown
          v-for="(levels, key) in (effectiveParams?.factors_ops ?? {})"
          :key="String(key)"
          :factor="{
            name: String(key),
            label: FACTOR_LABELS[String(key)] ?? String(key),
            levels: normalizeLevels(levels as Record<string, unknown>),
          }"
          :model-value="form.factors_ops[String(key)]"
          @update:model-value="(v: string) => (form.factors_ops[String(key)] = v)"
        />
        <div
          class="factor-chain-preview"
          data-testid="ops-factor-preview"
        >
          实时 ops_factor 链 = <strong>{{ opsFactorPreview.toFixed(2) }}</strong>
        </div>
      </fieldset>

      <fieldset v-else-if="currentStep === 6 && !form.include_ops">
        <legend>运维调整因子</legend>
        <p
          class="placeholder"
          data-testid="ops-skip"
        >
          本项目未启用运维，跳过运维因子。
        </p>
      </fieldset>

      <fieldset v-else-if="currentStep === 7">
        <legend>确认</legend>
        <dl
          class="confirm-list"
          data-testid="confirm-summary"
        >
          <dt>项目名</dt>
          <dd data-field="name">
            {{ form.name }}
          </dd>

          <dt>城市 / 行业</dt>
          <dd>{{ form.city }} / {{ form.industry }}</dd>

          <dt>客户 / 评估方</dt>
          <dd>
            {{ form.client || "—" }} / {{ form.evaluator || "—" }}
          </dd>

          <dt>类型</dt>
          <dd>{{ PROJECT_TYPE_LABELS[form.project_type] }}</dd>

          <template v-if="form.project_type === 'dev_and_ops'">
            <dt>α</dt>
            <dd>{{ form.alpha.toFixed(2) }}</dd>
          </template>

          <dt>阶段</dt>
          <dd>
            {{ form.phase }} (CF =
            {{ (effectiveParams?.cf?.[form.phase] ?? 1).toFixed(2) }})
          </dd>

          <dt>模式</dt>
          <dd>
            {{ form.mode === "forward"
              ? "正向"
              : `反向（目标 ${form.target_total} 元）` }}
          </dd>

          <dt>开发因子</dt>
          <dd>
            <ul class="factor-list">
              <template
                v-for="(v, k) in form.factors_dev"
                :key="String(k)"
              >
                <li v-if="v">
                  {{ FACTOR_LABELS[String(k)] ?? String(k) }}: {{ v }}
                </li>
              </template>
              <li v-if="!hasAnyFactor(form.factors_dev)">
                未配置（按 1.0 计算）
              </li>
            </ul>
          </dd>

          <template v-if="form.include_ops">
            <dt>运维因子</dt>
            <dd>
              <ul class="factor-list">
                <template
                  v-for="(v, k) in form.factors_ops"
                  :key="String(k)"
                >
                  <li v-if="v">
                    {{ FACTOR_LABELS[String(k)] ?? String(k) }}: {{ v }}
                  </li>
                </template>
                <li v-if="!hasAnyFactor(form.factors_ops)">
                  未配置（按 1.0 计算）
                </li>
              </ul>
            </dd>
          </template>
        </dl>
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
.hint {
  margin: 0 0 var(--space-2);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
.factor-chain-preview {
  margin-top: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--color-primary-bg, var(--color-bg));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-body);
}
.factor-chain-preview strong {
  color: var(--color-primary);
  font-weight: 600;
  margin-left: var(--space-1);
}
.radio-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.radio,
.checkbox {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-body);
  cursor: pointer;
}
.checkbox input[type="checkbox"]:disabled + span {
  color: var(--color-text-muted);
}
.confirm-list {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: var(--space-2) var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-body);
}
.confirm-list dt {
  font-weight: 600;
  color: var(--color-text-muted);
}
.confirm-list dd {
  margin: 0;
}
.factor-list {
  margin: 0;
  padding-left: var(--space-4);
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
