import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
  type Router,
  type RouterHistory,
} from "vue-router";
import { AUTH_TOKEN_KEY } from "@/api/client";

export function extractTokenFromUrl(url: string = window.location.href): void {
  const u = new URL(url);
  const token = u.searchParams.get("t");
  if (token) {
    sessionStorage.setItem(AUTH_TOKEN_KEY, token);
  }
}

/**
 * 把 dirty-checker 注入路由内置 slot。
 *
 * 单实例契约：同一时刻只有一个 dirty checker — 见 useUnsavedGuard 顶部 JSDoc。
 */
export function setDirtyChecker(router: Router, fn: () => boolean): void {
  (router as unknown as { __setDirtyChecker?: (fn: () => boolean) => void }).__setDirtyChecker?.(
    fn,
  );
}

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "project-list",
    component: () => import("@/views/ProjectList.vue"),
  },
  {
    path: "/projects/new",
    name: "project-wizard",
    component: () => import("@/views/ProjectWizard.vue"),
  },
  {
    path: "/projects/:id/functions",
    name: "fp-editor",
    component: () => import("@/views/FpEditor.vue"),
    props: (route) => ({ projectId: String(route.params.id) }),
  },
  {
    path: "/projects/:id/parameters",
    name: "param-manager",
    component: () => import("@/views/ParamManager.vue"),
    props: (route) => ({ projectId: String(route.params.id) }),
  },
  {
    path: "/projects/:id/result",
    name: "result-view",
    component: () => import("@/views/ResultView.vue"),
    props: (route) => ({ projectId: String(route.params.id) }),
  },
  {
    // v2.0 T21 — per-project audit timeline (GAP-J 前端).
    path: "/projects/:id/audit",
    name: "project-audit",
    component: () => import("@/views/AuditView.vue"),
  },
  {
    path: "/params/global",
    name: "params-global",
    component: () => import("@/views/ParamManager.vue"),
    props: () => ({ projectId: null }),
  },
  {
    path: "/reports",
    name: "report-center",
    component: () => import("@/views/ReportCenterView.vue"),
  },
  {
    path: "/audit",
    name: "audit-global",
    component: () => import("@/views/AuditGlobalView.vue"),
  },
  {
    // SPA fallback: any unmatched URL resolves here so users see a real
    // "page not found" instead of a blank body under the layout shell.
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: () => import("@/views/NotFound.vue"),
  },
];

export function createRouterFor(history: RouterHistory) {
  const router = createRouter({ history, routes });

  let pendingDirty: () => boolean = () => false;
  router.beforeEach((_to, _from, next) => {
    if (pendingDirty()) {
      const ok = window.confirm("有未保存的改动，确认离开此页？");
      if (!ok) return next(false);
    }
    next();
  });

  (router as unknown as { __setDirtyChecker: (fn: () => boolean) => void }).__setDirtyChecker = (
    fn,
  ) => {
    pendingDirty = fn;
  };

  return router;
}

export const router = createRouterFor(createWebHistory());
