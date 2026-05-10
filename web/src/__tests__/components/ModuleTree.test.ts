import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ModuleTree from "@/components/ModuleTree.vue";

describe("ModuleTree", () => {
  it("根据 functions 列表聚合 subsystem → module_l1", () => {
    const w = mount(ModuleTree, {
      props: {
        functions: [
          { id: 1, subsystem: "用户子系统", module_l1: "登录", category: "EI", us: 5 },
          { id: 2, subsystem: "用户子系统", module_l1: "注册", category: "EO", us: 7 },
          { id: 3, subsystem: "订单子系统", module_l1: "下单", category: "EI", us: 10 },
        ],
      },
    });
    expect(w.text()).toContain("用户子系统");
    expect(w.text()).toContain("订单子系统");
    expect(w.text()).toContain("登录");
  });

  it("点击叶子节点 emit select", async () => {
    const w = mount(ModuleTree, {
      props: {
        functions: [{ id: 1, subsystem: "A", module_l1: "B", category: "EI", us: 1 }],
      },
    });
    await w.find("[data-test='leaf']").trigger("click");
    expect(w.emitted().select).toBeTruthy();
  });
});
