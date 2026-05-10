import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import path from "node:path";

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  test: {
    environment: "happy-dom",
    globals: true,
    setupFiles: ["src/__tests__/setup.ts"],
    // Exclude Playwright e2e specs — they run via `pnpm test:e2e`, not vitest
    exclude: ["**/node_modules/**", "**/dist/**", "tests/e2e/**"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
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
