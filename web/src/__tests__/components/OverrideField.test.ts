import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import OverrideField from "@/components/OverrideField.vue";

describe("OverrideField", () => {
  it("默认非覆盖：不显示自定义徽章", () => {
    const w = mount(OverrideField, {
      props: { label: "PDR P50", modelValue: 6.41, defaultValue: 6.41 },
    });
    expect(w.find("[data-test='override-badge']").exists()).toBe(false);
  });

  it("modelValue ≠ defaultValue：显示自定义徽章 + 高亮容器", () => {
    const w = mount(OverrideField, {
      props: { label: "PDR P50", modelValue: 7.0, defaultValue: 6.41 },
    });
    expect(w.find("[data-test='override-badge']").exists()).toBe(true);
    expect(w.find("[data-overridden='true']").exists()).toBe(true);
  });

  it("点击恢复默认：emit reset", async () => {
    const w = mount(OverrideField, {
      props: { label: "x", modelValue: 7.0, defaultValue: 6.41 },
    });
    await w.find("[data-test='reset-btn']").trigger("click");
    expect(w.emitted().reset).toBeTruthy();
  });
});
