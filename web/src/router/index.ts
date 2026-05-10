// Minimal scaffolding stub. Replaced by Task 5 (Router + token 提取 + 未保存改动守卫).
import { createRouter, createWebHashHistory } from "vue-router";

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    // T5 会替换：当前用 catch-all 抑制 vue-router "no match" 警告
    { path: "/:pathMatch(.*)*", component: { template: "<div/>" } },
  ],
});
