import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "node:path";
import { readFileSync } from "node:fs";

const pkg = JSON.parse(
  readFileSync(path.resolve(__dirname, "package.json"), "utf-8"),
) as { version: string };

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
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
        // 把重量级 vendor 拆出独立 chunk，避免初始 index.js 一坨 1.6MB。
        // 顺序按 weight 排：先匹配 vxe-table（最大），再 element-plus，最后
        // vue 三件套。其它依赖落入默认 vendor chunk。
        manualChunks(id: string) {
          if (!id.includes("node_modules")) return;
          if (id.includes("element-plus") || id.includes("@element-plus"))
            return "vendor-element";
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
