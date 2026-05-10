import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ModuleTree from "@/components/ModuleTree.vue";

describe("ModuleTree", () => {
  it("根据 functions 列表聚合 subsystem → l1_module", () => {
    const w = mount(ModuleTree, {
      props: {
        functions: [
          { id: "f-1", subsystem: "用户子系统", l1_module: "登录", category: "EI", us: 5 },
          { id: "f-2", subsystem: "用户子系统", l1_module: "注册", category: "EO", us: 7 },
          { id: "f-3", subsystem: "订单子系统", l1_module: "下单", category: "EI", us: 10 },
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
        functions: [{ id: "f-1", subsystem: "A", l1_module: "B", category: "EI", us: 1 }],
      },
    });
    await w.find("[data-test='leaf']").trigger("click");
    expect(w.emitted().select).toBeTruthy();
  });
});
