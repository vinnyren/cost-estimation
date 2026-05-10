import { onMounted, onBeforeUnmount, type Ref } from "vue";
import { useRouter } from "vue-router";

export function useUnsavedGuard(isDirty: Ref<boolean>): void {
  const router = useRouter();

  function onBeforeUnload(e: BeforeUnloadEvent): void {
    if (isDirty.value) {
      e.preventDefault();
      e.returnValue = "";
    }
  }

  onMounted(() => {
    const setter = (router as unknown as { __setDirtyChecker?: (fn: () => boolean) => void })
      .__setDirtyChecker;
    setter?.(() => isDirty.value);

    window.addEventListener("beforeunload", onBeforeUnload);
  });

  onBeforeUnmount(() => {
    const setter = (router as unknown as { __setDirtyChecker?: (fn: () => boolean) => void })
      .__setDirtyChecker;
    setter?.(() => false);
    window.removeEventListener("beforeunload", onBeforeUnload);
  });
}
