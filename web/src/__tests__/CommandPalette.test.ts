import { describe, it, expect, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia, setActivePinia } from "pinia";
import { useProjectsStore } from "@/stores/projects";
import CommandPalette from "@/components/shell/CommandPalette.vue";

describe("CommandPalette", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    const store = useProjectsStore();
    // @ts-expect-error — direct mutation for test
    store.list = [
      { id: "p-001", name: "政务平台", city: "北京", industry: "电子政务" },
      { id: "p-002", name: "税务系统", city: "杭州", industry: "金融" },
    ];
  });

  it("filters projects by query", async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/", component: { template: "<div/>" } }] });
    const w = mount(CommandPalette, { props: { open: true }, global: { plugins: [router] } });
    await w.find(".palette-input").setValue("税务");
    const items = w.findAll(".palette-item");
    expect(items.length).toBe(1);
    expect(items[0].text()).toContain("税务系统");
  });

  it("emits update:open when esc pressed", async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/", component: { template: "<div/>" } }] });
    const w = mount(CommandPalette, { props: { open: true }, global: { plugins: [router] } });
    await w.find(".palette-input").trigger("keydown", { key: "Escape" });
    expect(w.emitted("update:open")?.[0]).toEqual([false]);
  });
});
