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

  it.skip("注入 oklch 设计 token", () => {
    const root = getComputedStyle(document.documentElement);
    expect(root.getPropertyValue("--color-accent").trim()).not.toBe("");
  });
});
