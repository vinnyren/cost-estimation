import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import Sidebar from "@/components/shell/Sidebar.vue";

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: "/", name: "home", component: { template: "<div/>" } },
    { path: "/params/global", name: "pg", component: { template: "<div/>" } },
    { path: "/projects/:id/functions", name: "fp", component: { template: "<div/>" } },
  ],
});

describe("Sidebar", () => {
  it("highlights active main nav item by route", async () => {
    await router.push("/");
    await router.isReady();
    const w = mount(Sidebar, { global: { plugins: [router] } });
    const items = w.findAll(".nav-item");
    expect(items[0].classes()).toContain("active");
  });

  it("hides project nav when not on a project route", async () => {
    await router.push("/");
    const w = mount(Sidebar, { global: { plugins: [router] } });
    expect(w.text()).not.toContain("FP 编辑");
  });

  it("shows project nav when on /projects/:id/*", async () => {
    await router.push("/projects/p-abc/functions");
    const w = mount(Sidebar, { global: { plugins: [router] } });
    expect(w.text()).toContain("FP 编辑");
  });

  it("marks 模板与场景 as disabled", () => {
    const w = mount(Sidebar, { global: { plugins: [router] } });
    const disabled = w.findAll(".nav-item.disabled");
    expect(disabled.length).toBe(1);
    expect(disabled[0].text()).toContain("模板与场景");
  });
});
