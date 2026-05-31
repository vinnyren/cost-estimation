import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import path from "node:path";
import { readFileSync } from "node:fs";

// 版本号单一来源：与 vite.config.ts 一致，从 .claude-plugin/plugin.json 注入
// __APP_VERSION__，使挂载组件的单测能解析该构建期全局常量。
const pluginManifest = JSON.parse(
  readFileSync(
    path.resolve(__dirname, "../.claude-plugin/plugin.json"),
    "utf-8",
  ),
) as { version: string };

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  define: {
    __APP_VERSION__: JSON.stringify(pluginManifest.version),
  },
  test: {
    environment: "happy-dom",
    globals: true,
    setupFiles: ["src/__tests__/setup.ts"],
    // Exclude Playwright e2e specs — they run via `pnpm test:e2e`, not vitest
    exclude: ["**/node_modules/**", "**/dist/**", "tests/e2e/**"],
    coverage: {
      provider: "v8",
      // v2.1 — json-summary lets the baseline check script (T14) parse totals from JSON.
      reporter: ["text", "html", "json-summary"],
      reportsDirectory: "./coverage",
      // Exclude untestable bootstrap (main.ts), pure type files, config files,
      // and test files themselves from coverage. Without these exclusions the
      // app entry drags functions/branches well below 80% even with full
      // unit-test coverage of the testable surface.
      include: ["src/**/*.{ts,vue}"],
      exclude: [
        "src/main.ts",
        "src/api/types.ts",
        "src/**/*.d.ts",
        "src/__tests__/**",
        "**/node_modules/**",
        "**/dist/**",
      ],
      thresholds: { lines: 80, statements: 80, functions: 80, branches: 80 },
    },
  },
});
