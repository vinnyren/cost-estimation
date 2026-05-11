<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import { useProjectsStore } from "@/stores/projects";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ "update:open": [value: boolean] }>();

const router = useRouter();
const store = useProjectsStore();
const query = ref("");
const inputRef = ref<HTMLInputElement | null>(null);
const activeIdx = ref(0);

const results = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return store.items.slice(0, 8);
  return store.items
    .filter((p) =>
      p.name.toLowerCase().includes(q) ||
      p.id.toLowerCase().includes(q) ||
      (p.client ?? "").toLowerCase().includes(q) ||
      p.city.toLowerCase().includes(q)
    )
    .slice(0, 8);
});

watch(() => props.open, async (isOpen) => {
  if (isOpen) {
    query.value = "";
    activeIdx.value = 0;
    await nextTick();
    inputRef.value?.focus();
  }
});

function close() { emit("update:open", false); }
function select(idx: number) {
  const project = results.value[idx];
  if (!project) return;
  router.push(`/projects/${project.id}/functions`);
  close();
}
function onKey(e: KeyboardEvent) {
  if (e.key === "Escape") close();
  if (e.key === "ArrowDown") { e.preventDefault(); activeIdx.value = Math.min(activeIdx.value + 1, results.value.length - 1); }
  if (e.key === "ArrowUp") { e.preventDefault(); activeIdx.value = Math.max(activeIdx.value - 1, 0); }
  if (e.key === "Enter") select(activeIdx.value);
}
</script>

<template>
  <div v-if="open" class="palette-backdrop" @click="close">
    <div class="palette" role="dialog" aria-label="命令面板" @click.stop>
      <input
        ref="inputRef"
        class="palette-input"
        v-model="query"
        placeholder="搜索项目名 / 编码 / 客户 / 城市..."
        @keydown="onKey"
      />
      <div class="palette-list">
        <div v-if="results.length === 0" class="palette-empty">
          无匹配项目 · 试试新建项目?
        </div>
        <div
          v-for="(p, i) in results"
          :key="p.id"
          class="palette-item"
          :class="{ active: i === activeIdx }"
          @click="select(i)"
          @mouseenter="activeIdx = i"
        >
          <div class="palette-name">{{ p.name }}</div>
          <div class="palette-meta mono">
            {{ p.id }} · {{ p.city }} · {{ p.industry }}
          </div>
        </div>
      </div>
      <div class="palette-foot mono">
        <span>↑↓ 选择</span><span>↵ 进入</span><span>esc 关闭</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.palette-backdrop {
  position: fixed; inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: grid; place-items: start center;
  padding-top: 12vh; z-index: 1000;
}
.palette {
  width: 560px; max-width: 92vw;
  background: var(--surface); border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}
.palette-input {
  width: 100%; padding: 14px 18px;
  border: 0; outline: 0;
  font-size: 14px;
  border-bottom: 1px solid var(--border);
}
.palette-list { max-height: 50vh; overflow-y: auto; padding: 6px; }
.palette-empty { padding: 30px; text-align: center; color: var(--text-3); font-size: 12px; }
.palette-item {
  padding: 8px 12px; border-radius: var(--radius); cursor: pointer;
}
.palette-item.active { background: var(--accent-soft); }
.palette-name { font-weight: 500; color: var(--text); }
.palette-meta { color: var(--text-3); font-size: 11px; margin-top: 2px; }
.palette-foot {
  padding: 8px 18px; border-top: 1px solid var(--border);
  display: flex; gap: 16px; font-size: 11px; color: var(--text-3);
}
</style>
