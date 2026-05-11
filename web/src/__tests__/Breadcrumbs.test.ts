import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia, setActivePinia } from "pinia";
import Breadcrumbs from "@/components/shell/Breadcrumbs.vue";

describe("Breadcrumbs", () => {
  it("shows 项目工作台 + 新建项目 on wizard route", async () => {
    setActivePinia(createPinia());
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/", name: "project-list", component: { template: "<div/>" } },
        { path: "/projects/new", name: "project-wizard", component: { template: "<div/>" } },
      ],
    });
    await router.push("/projects/new");
    await router.isReady();
    const w = mount(Breadcrumbs, { global: { plugins: [router] } });
    expect(w.text()).toContain("项目工作台");
    expect(w.text()).toContain("新建项目");
  });
});
