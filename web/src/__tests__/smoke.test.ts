import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import App from "../App.vue";

describe("App smoke", () => {
  it("挂载根组件且暴露 router-view", () => {
    const wrapper = mount(App, {
      global: {
        stubs: { "router-view": { template: "<div data-test='rv'/>" } },
      },
    });
    expect(wrapper.find("[data-test='rv']").exists()).toBe(true);
  });

  // 注：happy-dom 不解析 import 的 CSS 到 CSSOM/computed style — 需 Playwright 等真实浏览器环境
  // 此用例保留 skip 状态，待 E2E 阶段在真实浏览器中验证 oklch 设计 token 的注入。
  it.skip("注入 oklch 设计 token", () => {
    const root = getComputedStyle(document.documentElement);
    expect(root.getPropertyValue("--color-accent").trim()).not.toBe("");
  });
});
