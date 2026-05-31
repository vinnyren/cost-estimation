/// <reference types="vite/client" />

// 由 vite.config.ts 的 define 注入，构建期从 .claude-plugin/plugin.json 读取（版本单一来源）。
declare const __APP_VERSION__: string;
