import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import LoadingSkeleton from "@/components/status/LoadingSkeleton.vue";
import EmptyState from "@/components/status/EmptyState.vue";
import ErrorBanner from "@/components/status/ErrorBanner.vue";
import StaleBanner from "@/components/status/StaleBanner.vue";

describe("Status components", () => {
  it("LoadingSkeleton 渲染指定行数", () => {
    const wrapper = mount(LoadingSkeleton, { props: { rows: 8 } });
    expect(wrapper.findAll("[data-test='skeleton-row']")).toHaveLength(8);
  });

  it("EmptyState 显示 title + cta-label", () => {
    const wrapper = mount(EmptyState, {
      props: { title: "项目库为空", ctaLabel: "新建第一个项目" },
    });
    expect(wrapper.text()).toContain("项目库为空");
    expect(wrapper.find("button").text()).toBe("新建第一个项目");
  });

  it("ErrorBanner 显示 problem + cause + 重试按钮", () => {
    const wrapper = mount(ErrorBanner, {
      props: {
        problem: "无法加载项目",
        cause: "网络断开",
        suggestion: "请检查网络连接后重试",
        retryable: true,
      },
    });
    expect(wrapper.text()).toContain("无法加载项目");
    expect(wrapper.text()).toContain("网络断开");
    expect(wrapper.find("[data-test='retry']").exists()).toBe(true);
  });

  it("ErrorBanner 用 role=alert 暴露给屏幕阅读器", () => {
    const wrapper = mount(ErrorBanner, {
      props: { problem: "x", cause: "y", suggestion: "z" },
    });
    expect(wrapper.find("[role='alert']").exists()).toBe(true);
  });

  it("StaleBanner 触发 recompute 事件", async () => {
    const wrapper = mount(StaleBanner);
    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted().recompute).toBeTruthy();
  });
});
