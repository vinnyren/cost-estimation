import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";
import StaleBanner from "@/components/status/StaleBanner.vue";
import EmptyState from "@/components/status/EmptyState.vue";
import OverrideField from "@/components/OverrideField.vue";

describe("a11y baseline", () => {
  it("LoadingSkeleton 暴露 role=status + aria-busy=true", () => {
    const w = mount(LoadingSkeleton, { props: { rows: 3 } });
    const root = w.find("[role='status']");
    expect(root.exists()).toBe(true);
    expect(root.attributes("aria-busy")).toBe("true");
  });

  it("ErrorBanner 暴露 role=alert", () => {
    const w = mount(ErrorBanner, {
      props: {
        problem: "加载失败",
        cause: "网络异常",
        suggestion: "请重试",
      },
    });
    expect(w.find("[role='alert']").exists()).toBe(true);
  });

  it("StaleBanner 暴露 role=status + aria-live=polite", () => {
    const w = mount(StaleBanner);
    const root = w.find("[role='status']");
    expect(root.exists()).toBe(true);
    expect(root.attributes("aria-live")).toBe("polite");
  });

  it("EmptyState CTA 触摸目标 ≥ 44px（min-height/min-width 在 CSS 中）", () => {
    const w = mount(EmptyState, {
      props: { title: "项目库为空", ctaLabel: "新建第一个项目" },
    });
    const btn = w.find("button");
    expect(btn.exists()).toBe(true);
    // happy-dom 不计算 layout，但我们至少能确认按钮存在且类型正确
    // 实际触摸目标尺寸由 EmptyState.vue 中 button { min-height:44px; min-width:120px } 保证
    expect(btn.element.tagName).toBe("BUTTON");
    expect(btn.attributes("type")).toBe("button");
  });

  it("OverrideField reset 按钮带 aria-label", async () => {
    const w = mount(OverrideField, {
      props: { label: "PDR P50", modelValue: 7.0, defaultValue: 6.41 },
    });
    const btn = w.find("[data-test='reset-btn']");
    expect(btn.exists()).toBe(true);
    expect(btn.attributes("aria-label")).toBe("恢复 PDR P50 为默认值");
  });
});
