import { defineStore } from "pinia";
import { ref } from "vue";
import { paramsApi, type EffectiveParams } from "@/api/params";

export const useParamsStore = defineStore("params", () => {
  const effective = ref<EffectiveParams | null>(null);
  const overrides = ref<Record<string, unknown>>({});
  const loadedFor = ref<string | null>(null);

  async function loadFor(projectId: string): Promise<void> {
    const resp = await paramsApi.effective(projectId);
    effective.value = resp;
    overrides.value = ((resp?.overrides ?? {}) as Record<string, unknown>);
    loadedFor.value = projectId;
  }

  async function loadGlobal(): Promise<void> {
    const resp = await paramsApi.global();
    effective.value = resp;
    overrides.value = ((resp?.overrides ?? {}) as Record<string, unknown>);
    loadedFor.value = null; // global mode marker
  }

  async function applyOverride(
    projectId: string,
    patch: Record<string, unknown>,
  ): Promise<void> {
    const resp = await paramsApi.override(projectId, patch);
    effective.value = resp;
    overrides.value = ((resp?.overrides ?? {}) as Record<string, unknown>);
  }

  function isOverridden(path: string): boolean {
    if (!overrides.value) return false;
    // 直接 key 命中
    if (path in overrides.value) return true;
    // 嵌套 path 命中（如 city_rate.北京.dev）
    const parts = path.split(".");
    let cur: unknown = overrides.value;
    for (const p of parts) {
      if (cur && typeof cur === "object" && p in (cur as Record<string, unknown>)) {
        cur = (cur as Record<string, unknown>)[p];
      } else {
        return false;
      }
    }
    return true;
  }

  return { effective, overrides, loadedFor, loadFor, loadGlobal, applyOverride, isOverridden };
});
