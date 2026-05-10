import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ResultCard from "@/components/ResultCard.vue";

describe("ResultCard", () => {
  it("P50 显示推荐徽章", () => {
    const w = mount(ResultCard, {
      props: { band: "P50", value: 489180, unit: "元", recommended: true },
    });
    expect(w.text()).toContain("推荐");
    expect(w.find("[data-recommended='true']").exists()).toBe(true);
  });

  it("P10/P90 不显示推荐徽章", () => {
    const w = mount(ResultCard, { props: { band: "P10", value: 100000, unit: "元" } });
    expect(w.text()).not.toContain("推荐");
  });

  it("displayValue 自动转万元", () => {
    const w = mount(ResultCard, {
      props: { band: "P50", value: 489180, unit: "元", recommended: true },
    });
    expect(w.text()).toContain("48.92");
    expect(w.text()).toContain("万元");
  });
});
