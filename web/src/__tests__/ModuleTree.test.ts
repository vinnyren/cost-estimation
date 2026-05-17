import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ModuleTree from "@/components/ModuleTree.vue";
import type { FunctionPoint } from "@/api/functions";

const fps: Pick<
  FunctionPoint,
  "id" | "subsystem" | "l1_module" | "category" | "us"
>[] = [
  { id: "1", subsystem: "软件开发", l1_module: "财务管理", category: "EI", us: 4 },
  { id: "2", subsystem: "软件开发", l1_module: "财务管理", category: "EO", us: 5 },
  { id: "3", subsystem: "软件开发", l1_module: "电子结算", category: "EQ", us: 4 },
];

describe("ModuleTree (v2.5)", () => {
  it("renders 全部 entry with total count", () => {
    const w = mount(ModuleTree, { props: { functions: fps } });
    const all = w.find('[data-test="all"]');
    expect(all.exists()).toBe(true);
    expect(all.text()).toContain("全部功能点");
    expect(all.text()).toContain("3");
  });

  it("renders module leaves grouped by l1_module with counts", () => {
    const w = mount(ModuleTree, { props: { functions: fps } });
    const leaves = w.findAll('[data-test="leaf"]');
    expect(leaves).toHaveLength(2); // 财务管理 + 电子结算
    expect(leaves[0].text()).toContain("财务管理");
    expect(leaves[0].text()).toContain("2");
  });

  it("emits select with module payload when a leaf clicked", async () => {
    const w = mount(ModuleTree, { props: { functions: fps } });
    await w.findAll('[data-test="leaf"]')[0].trigger("click");
    expect(w.emitted("select")?.[0]).toEqual([
      { subsystem: "软件开发", l1_module: "财务管理" },
    ]);
  });

  it("emits select with null when 全部 clicked", async () => {
    const w = mount(ModuleTree, { props: { functions: fps } });
    await w.findAll('[data-test="leaf"]')[0].trigger("click"); // select a module first
    await w.find('[data-test="all"]').trigger("click");
    const events = w.emitted("select");
    expect(events?.[events.length - 1]).toEqual([null]);
  });

  it("marks the clicked leaf as active", async () => {
    const w = mount(ModuleTree, { props: { functions: fps } });
    const leaf = w.findAll('[data-test="leaf"]')[0];
    await leaf.trigger("click");
    expect(leaf.classes()).toContain("active");
  });
});
