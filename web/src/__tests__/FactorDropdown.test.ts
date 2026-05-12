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

const factorForMeta = {
  name: "app_type",
  label: "应用类型",
  levels: {
    "业务处理": { multiplier: 1.0 },
    "基础软件": { multiplier: 1.5 },
  },
};

const meta = {
  label: "应用类型",
  description: "项目所属软件应用领域",
  options: {
    "业务处理": { label: "业务处理（OLTP）", description: "在线事务处理" },
    "基础软件": { label: "基础软件", description: "操作系统、中间件" },
  },
};

describe("FactorDropdown v2.5 meta", () => {
  it("renders option label from meta when provided", () => {
    const w = mount(FactorDropdown, { props: { factor: factorForMeta, modelValue: undefined, meta } });
    expect(w.text()).toContain("业务处理（OLTP）");
    expect(w.text()).toContain("基础软件");
  });

  it("falls back to factor.label when no meta", () => {
    const w = mount(FactorDropdown, { props: { factor: factorForMeta, modelValue: undefined } });
    expect(w.text()).toContain("应用类型");
  });

  it("ⓘ title attr contains factor description from meta", () => {
    const w = mount(FactorDropdown, { props: { factor: factorForMeta, modelValue: undefined, meta } });
    const tip = w.find('span[title]');
    expect(tip.exists()).toBe(true);
    expect(tip.attributes("title")).toBe("项目所属软件应用领域");
  });
});
