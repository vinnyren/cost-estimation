import { ref, type Ref } from "vue";
import { ApiError } from "@/api/client";

export type ApiState = "idle" | "loading" | "success" | "error" | "partial";

export interface UseApiReturn<TArgs extends unknown[], TData> {
  state: Ref<ApiState>;
  data: Ref<TData | null>;
  error: Ref<ApiError | null>;
  run: (...args: TArgs) => Promise<TData>;
  reset: () => void;
}

export function useApi<TArgs extends unknown[], TData>(
  fn: (...args: TArgs) => Promise<TData>,
): UseApiReturn<TArgs, TData> {
  const state = ref<ApiState>("idle");
  const data = ref<TData | null>(null) as Ref<TData | null>;
  const error = ref<ApiError | null>(null);

  async function run(...args: TArgs): Promise<TData> {
    state.value = "loading";
    error.value = null;
    try {
      const result = await fn(...args);
      data.value = result;
      state.value = "success";
      return result;
    } catch (e) {
      const apiErr = e instanceof ApiError ? e : new ApiError("UNKNOWN", String(e));
      error.value = apiErr;
      state.value = "error";
      throw apiErr;
    }
  }

  function reset(): void {
    state.value = "idle";
    data.value = null;
    error.value = null;
  }

  return { state, data, error, run, reset };
}
