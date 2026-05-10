import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import FactorDropdown from "@/components/FactorDropdown.vue";

describe("FactorDropdown", () => {
  const def = {
    name: "app_type",
    label: "应用类型",
    levels: {
      OLTP: { multiplier: 1.0 },
      OLAP: { multiplier: 1.1 },
    },
  };

  it("renders options with multipliers", () => {
    const w = mount(FactorDropdown, {
      props: { factor: def, modelValue: "OLTP" },
    });
    expect(w.text()).toContain("OLTP");
    expect(w.text()).toContain("1.00");
  });

  it("emits update:modelValue on select", async () => {
    const w = mount(FactorDropdown, {
      props: { factor: def, modelValue: "OLTP" },
    });
    await w.find("select").setValue("OLAP");
    expect(w.emitted("update:modelValue")![0]).toEqual(["OLAP"]);
  });

  it("renders label + factor name", () => {
    const w = mount(FactorDropdown, {
      props: { factor: def, modelValue: undefined },
    });
    expect(w.text()).toContain("应用类型");
    expect(w.text()).toContain("app_type");
  });

  it("renders level description when present", () => {
    const defWithDesc = {
      name: "app_type",
      label: "应用类型",
      levels: {
        OLTP: { multiplier: 1.0, description: "联机事务" },
      },
    };
    const w = mount(FactorDropdown, {
      props: { factor: defWithDesc, modelValue: "OLTP" },
    });
    expect(w.text()).toContain("联机事务");
  });

  it("falls back to empty value when modelValue is undefined", () => {
    const w = mount(FactorDropdown, {
      props: { factor: def, modelValue: undefined },
    });
    const select = w.find("select").element as HTMLSelectElement;
    expect(select.value).toBe("");
  });
});
