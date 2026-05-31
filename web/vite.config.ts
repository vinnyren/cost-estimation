import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "node:path";
import { readFileSync } from "node:fs";

// 版本号单一来源：从插件根 .claude-plugin/plugin.json 读取（权威源），
// 而非 package.json，使前端显示版本恒等于产品版本。
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
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8788", changeOrigin: false },
      "/health": { target: "http://127.0.0.1:8788", changeOrigin: false },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: true,
    rollupOptions: {
      output: {
        // 把 vue 三件套拆出独立 chunk，避免初始 index.js 加载放大。
        // element-plus 与 vxe-table 在 v2.0 已移除（项目使用原生 HTML + scoped
        // CSS，不需要 UI 组件库），相应 chunk 也一并移除。
        manualChunks(id: string) {
          if (!id.includes("node_modules")) return;
          if (
            id.includes("/vue/") ||
            id.includes("vue-router") ||
            id.includes("/pinia/") ||
            id.includes("@vue/")
          )
            return "vendor-vue";
        },
      },
    },
  },
});
