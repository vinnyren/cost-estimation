import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { ForwardResult, ReverseResult } from "@/api/calc";

export const useResultsStore = defineStore("results", () => {
  const forwardResult = ref<ForwardResult | null>(null);
  const reverseResult = ref<ReverseResult | null>(null);
  const lastComputedAt = ref<number>(0);
  const paramsChangedAt = ref<number>(0);

  const isStale = computed(
    () => lastComputedAt.value > 0 && paramsChangedAt.value > lastComputedAt.value,
  );

  function setForwardResult(r: ForwardResult): void {
    forwardResult.value = r;
    lastComputedAt.value = Date.now();
  }

  function setReverseResult(r: ReverseResult): void {
    reverseResult.value = r;
    lastComputedAt.value = Date.now();
  }

  function markParamsChanged(): void {
    // Guarantee strictly-greater timestamp to avoid same-millisecond ties with
    // a freshly-set lastComputedAt. Without this, paramsChangedAt === lastComputedAt
    // can occur on fast machines and isStale (strict >) returns false unexpectedly.
    const now = Date.now();
    paramsChangedAt.value = now > lastComputedAt.value ? now : lastComputedAt.value + 1;
  }

  function clear(): void {
    forwardResult.value = null;
    reverseResult.value = null;
    lastComputedAt.value = 0;
    paramsChangedAt.value = 0;
  }

  return {
    forwardResult,
    reverseResult,
    lastComputedAt,
    paramsChangedAt,
    isStale,
    setForwardResult,
    setReverseResult,
    markParamsChanged,
    clear,
  };
});
