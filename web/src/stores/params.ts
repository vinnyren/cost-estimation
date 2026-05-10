import { defineStore } from "pinia";
import { ref } from "vue";
import { paramsApi, type EffectiveParams } from "@/api/params";

export const useParamsStore = defineStore("params", () => {
  const effective = ref<EffectiveParams | null>(null);
  const overrides = ref<Record<string, unknown>>({});
  const loadedFor = ref<number | null>(null);

  async function loadFor(projectId: number): Promise<void> {
    const resp = await paramsApi.effective(projectId);
    effective.value = resp;
    overrides.value = (resp.overrides ?? {}) as Record<string, unknown>;
    loadedFor.value = projectId;
  }

  async function applyOverride(
    projectId: number,
    patch: Record<string, unknown>,
  ): Promise<void> {
    const resp = await paramsApi.override(projectId, patch);
    effective.value = resp;
    overrides.value = (resp.overrides ?? {}) as Record<string, unknown>;
  }

  function isOverridden(path: string): boolean {
    return path in overrides.value;
  }

  return { effective, overrides, loadedFor, loadFor, applyOverride, isOverridden };
});
