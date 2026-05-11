import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import FactorTable from "@/components/FactorTable.vue";

describe("FactorTable", () => {
  const factor = {
    name: "app_type",
    label: "应用类型",
    levels: {
      OLTP: { multiplier: 1.0, description: "联机事务" },
      OLAP: { multiplier: 1.1, description: "数据分析" },
      Web: { multiplier: 1.05, description: "Web 应用" },
    },
  };

  it("renders all levels with multipliers", () => {
    const w = mount(FactorTable, { props: { factor, scope: "global" } });
    expect(w.text()).toContain("应用类型");
    expect(w.text()).toContain("OLTP");
    expect(w.text()).toContain("1.00");
    expect(w.text()).toContain("1.10");
  });

  it("emits update:multiplier when input changes", async () => {
    const w = mount(FactorTable, { props: { factor, scope: "global" } });
    const inputs = w.findAll('input[type="number"]');
    await inputs[0].setValue("1.5");
    await inputs[0].trigger("change");
    expect(w.emitted("update:multiplier")).toBeTruthy();
    const evt = w.emitted("update:multiplier")![0];
    expect(evt[0]).toEqual({ levelKey: "OLTP", value: 1.5 });
  });

  it("renders factor.name as data-attribute", () => {
    const w = mount(FactorTable, { props: { factor, scope: "global" } });
    expect(w.find('[data-factor="app_type"]').exists()).toBe(true);
  });

  it("does not emit on invalid (negative) input", async () => {
    const w = mount(FactorTable, { props: { factor, scope: "global" } });
    const inputs = w.findAll('input[type="number"]');
    await inputs[0].setValue("-0.5");
    await inputs[0].trigger("change");
    expect(w.emitted("update:multiplier")).toBeFalsy();
  });
});
