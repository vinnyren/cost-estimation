<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { uploadsApi, type UploadRecord } from "@/api/uploads";

const props = defineProps<{ open: boolean; projectId: string }>();
const emit = defineEmits<{ "update:open": [v: boolean]; refreshed: [count: number] }>();

const items = ref<UploadRecord[]>([]);
const loading = ref(false);
const hint = ref("");

async function load() {
  loading.value = true;
  hint.value = "";
  try {
    items.value = await uploadsApi.list(props.projectId);
    emit("refreshed", items.value.length);
  } catch (e) {
    hint.value = e instanceof Error ? e.message : "加载失败";
  } finally {
    loading.value = false;
  }
}

async function onRemove(rec: UploadRecord) {
  if (!window.confirm(`确定删除「${rec.filename}」？删除后无法恢复。`)) return;
  try {
    await uploadsApi.remove(props.projectId, rec.id);
    await load();
  } catch (e) {
    hint.value = e instanceof Error ? e.message : "删除失败";
  }
}

function fmtSize(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function fmtTime(s: string): string {
  return s.replace("T", " ").slice(0, 16);
}

function close() { emit("update:open", false); }

watch(() => props.open, (v) => { if (v) load(); });
onMounted(() => { if (props.open) load(); });
</script>

<template>
  <div v-if="open" class="modal-backdrop" @click="close">
    <div class="card upload-modal" @click.stop>
      <div class="modal-head">
        <div>
          <div class="section-title">已上传文件</div>
          <div class="muted" style="font-size: 12px">项目 {{ projectId }} · 共 {{ items.length }} 个</div>
        </div>
        <button class="btn btn-ghost btn-sm" @click="close">关闭</button>
      </div>

      <div v-if="loading" class="muted" style="padding: 24px; text-align: center">加载中…</div>
      <div v-else-if="items.length === 0" class="muted" style="padding: 32px; text-align: center">
        暂无上传文件
      </div>
      <table v-else class="table" style="margin-top: 12px">
        <thead>
          <tr>
            <th>文件名</th>
            <th style="width: 100px">大小</th>
            <th style="width: 80px">类型</th>
            <th style="width: 130px">上传时间</th>
            <th style="width: 70px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in items" :key="r.id">
            <td><b>{{ r.filename }}</b></td>
            <td class="mono">{{ fmtSize(r.size) }}</td>
            <td><span class="badge">{{ r.filetype }}</span></td>
            <td class="muted mono" style="font-size: 11px">{{ fmtTime(r.uploaded_at) }}</td>
            <td>
              <button class="btn btn-sm btn-ghost" style="color: var(--red)" @click="onRemove(r)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="hint" class="banner banner-amber" style="margin-top: 12px">{{ hint }}</div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: grid; place-items: center;
  z-index: 1000;
}
.upload-modal { width: 720px; max-width: 92vw; padding: 24px; }
.modal-head { display: flex; align-items: flex-start; justify-content: space-between; }
</style>
