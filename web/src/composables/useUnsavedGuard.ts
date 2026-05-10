import { onMounted, onBeforeUnmount, type Ref } from "vue";
import { useRouter } from "vue-router";
import { setDirtyChecker } from "@/router";

/**
 * 路由级未保存改动守卫（单实例契约）。
 *
 * 注意：当前实现只支持同一时刻一个 guard 实例。多组件并发使用会导致后者
 * 覆盖前者的 dirty checker，前者卸载时还会把 slot 清成 () => false。
 * 若未来需要多个并发 guard，请把 router/index.ts 的 `pendingDirty` 升级
 * 为 `Set<() => boolean>` 并在守卫中 OR 聚合。
 */
export function useUnsavedGuard(isDirty: Ref<boolean>): void {
  const router = useRouter();

  function onBeforeUnload(e: BeforeUnloadEvent): void {
    if (isDirty.value) {
      e.preventDefault();
      e.returnValue = "";
    }
  }

  onMounted(() => {
    setDirtyChecker(router, () => isDirty.value);
    window.addEventListener("beforeunload", onBeforeUnload);
  });

  onBeforeUnmount(() => {
    setDirtyChecker(router, () => false);
    window.removeEventListener("beforeunload", onBeforeUnload);
  });
}
