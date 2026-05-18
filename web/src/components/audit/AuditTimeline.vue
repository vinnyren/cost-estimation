<script setup lang="ts">
import type { AuditEntry } from "@/api/audit";

defineProps<{ events: AuditEntry[]; showProject?: boolean }>();

function typeOf(e: AuditEntry): "user" | "calc" | "ai" | "system" {
  const a = e.action ?? "";
  if (a.includes("ai") || a.includes("extract") || a.includes("allocate")) return "ai";
  if (a.includes("calc")) return "calc";
  if (a.includes("snapshot") || a.includes("migration")) return "system";
  return "user";
}

const TYPE_LABELS: Record<string, string> = {
  user: "🙋", calc: "🧮", ai: "✨", system: "⚙️",
};
const TYPE_COLORS: Record<string, string> = {
  user: "var(--accent)", calc: "var(--text-2)", ai: "var(--purple)", system: "var(--text-3)",
};

const ACTION_LABELS: Record<string, string> = {
  "project.create": "✨ 创建项目",
  "project.update": "✏️ 修改项目",
  "project.delete": "🗑️ 删除项目",
  "project.copy": "📋 复制项目",
  "fp.create": "➕ 添加 FP",
  "fp.update": "✏️ 修改 FP",
  "fp.delete": "➖ 删除 FP",
  "fp.bulk_write": "📦 批量写入 FP",
  "fp.restore": "🔄 恢复 FP 快照",
  "params.override": "⚙️ 修改参数",
  "upload.create": "📁 上传文档",
  "upload.delete": "🗑️ 删除上传",
  "calc.run": "🧮 执行计算",
  "report.export": "📤 导出报告",
};

function label(action: string): string {
  return ACTION_LABELS[action] ?? action;
}

function projectName(e: AuditEntry): string {
  return (e as AuditEntry & { project_name?: string }).project_name ?? "";
}

function detail(e: AuditEntry): string {
  if (e.target) return e.target;
  if (e.diff_json) {
    try {
      const obj = JSON.parse(e.diff_json) as Record<string, unknown>;
      return Object.keys(obj).map(k => `${k}: ${String(obj[k])}`).join(" · ");
    } catch { return e.diff_json; }
  }
  return "";
}
</script>

<template>
  <div class="timeline">
    <div v-for="(e, i) in events" :key="e.id" class="tl-item">
      <div class="tl-dot" :style="{ background: TYPE_COLORS[typeOf(e)] }">
        {{ TYPE_LABELS[typeOf(e)] }}
      </div>
      <div v-if="i < events.length - 1" class="tl-line" />
      <div class="tl-body">
        <div class="tl-head">
          <span class="tl-title">{{ label(e.action) }}</span>
          <span class="tl-time mono">{{ e.ts }}</span>
        </div>
        <div class="tl-meta">
          <span
            v-if="showProject && 'project_name' in e"
            class="badge badge-blue"
          >{{ projectName(e) }}</span>
          <span class="badge" :class="`badge-${typeOf(e) === 'ai' ? 'purple' : typeOf(e) === 'calc' ? 'blue' : ''}`">
            {{ e.action }}
          </span>
          <span class="muted">{{ e.actor ?? '系统' }}</span>
          <span class="muted mono" style="font-size: 11px">#{{ e.id }}</span>
        </div>
        <div v-if="detail(e)" class="tl-desc">{{ detail(e) }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.timeline { position: relative; padding-left: 4px; }
.tl-item { position: relative; padding-left: 30px; padding-bottom: 20px; }
.tl-dot {
  position: absolute; left: 0; top: 0;
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--text-3); color: white;
  display: grid; place-items: center;
  font-size: 12px;
}
.tl-line {
  position: absolute; left: 10px; top: 22px; bottom: -2px;
  width: 2px; background: var(--border);
}
.tl-body { background: transparent; }
.tl-head { display: flex; justify-content: space-between; align-items: baseline; }
.tl-title { font-weight: 500; }
.tl-time { font-size: 11px; color: var(--text-3); }
.tl-meta { display: flex; align-items: center; gap: 8px; margin: 4px 0; }
.tl-desc { font-size: 12px; color: var(--text-2); margin-top: 4px; }
</style>
