import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { ref, defineComponent, type Ref } from "vue";
import { createMemoryHistory } from "vue-router";
import { useUnsavedGuard } from "@/composables/useUnsavedGuard";
import { createRouterFor } from "@/router";

function makeHostComponent(dirty: Ref<boolean>) {
  return defineComponent({
    setup() {
      useUnsavedGuard(dirty);
      return () => null;
    },
  });
}

describe("useUnsavedGuard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("mounted 时注册 beforeunload listener 并把 dirty checker 写进 router slot", async () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    const router = createRouterFor(createMemoryHistory());
    await router.push("/");
    await router.isReady();

    const dirty = ref(true);
    const Host = makeHostComponent(dirty);
    const wrapper = mount(Host, { global: { plugins: [router] } });

    expect(addSpy).toHaveBeenCalledWith("beforeunload", expect.any(Function));

    // dirty=true → 路由切换时应触发 confirm；先 stub confirm 让它返回 false → 阻断导航
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const before = router.currentRoute.value.fullPath;
    await router.push("/projects/new").catch(() => {});
    expect(confirmSpy).toHaveBeenCalled();
    expect(router.currentRoute.value.fullPath).toBe(before);

    wrapper.unmount();
  });

  it("unmount 后 dirty checker 复位，导航不再触发 confirm", async () => {
    const router = createRouterFor(createMemoryHistory());
    await router.push("/");
    await router.isReady();

    const dirty = ref(true);
    const Host = makeHostComponent(dirty);
    const wrapper = mount(Host, { global: { plugins: [router] } });

    wrapper.unmount();

    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    await router.push("/projects/new").catch(() => {});
    expect(confirmSpy).not.toHaveBeenCalled();
  });

  it("unmount 时移除 beforeunload listener", async () => {
    const removeSpy = vi.spyOn(window, "removeEventListener");
    const router = createRouterFor(createMemoryHistory());
    await router.push("/");
    await router.isReady();

    const dirty = ref(false);
    const Host = makeHostComponent(dirty);
    const wrapper = mount(Host, { global: { plugins: [router] } });
    wrapper.unmount();

    expect(removeSpy).toHaveBeenCalledWith("beforeunload", expect.any(Function));
  });

  it("dirty=true 时 beforeunload 调 preventDefault 并设置 returnValue", async () => {
    const router = createRouterFor(createMemoryHistory());
    await router.push("/");
    await router.isReady();

    const dirty = ref(true);
    const Host = makeHostComponent(dirty);
    const wrapper = mount(Host, { global: { plugins: [router] } });

    // 取注册的 listener — 直接派发 BeforeUnloadEvent 让浏览器调用它
    const event = new Event("beforeunload", { cancelable: true }) as BeforeUnloadEvent;
    const preventSpy = vi.spyOn(event, "preventDefault");
    window.dispatchEvent(event);

    expect(preventSpy).toHaveBeenCalled();

    wrapper.unmount();
  });

  it("dirty=false 时 beforeunload 不阻拦", async () => {
    const router = createRouterFor(createMemoryHistory());
    await router.push("/");
    await router.isReady();

    const dirty = ref(false);
    const Host = makeHostComponent(dirty);
    const wrapper = mount(Host, { global: { plugins: [router] } });

    const event = new Event("beforeunload", { cancelable: true }) as BeforeUnloadEvent;
    const preventSpy = vi.spyOn(event, "preventDefault");
    window.dispatchEvent(event);

    expect(preventSpy).not.toHaveBeenCalled();

    wrapper.unmount();
  });
});
