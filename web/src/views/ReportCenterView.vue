<script setup lang="ts">
import { ref, onMounted } from "vue";
import { projectsApi, type Project } from "@/api/projects";
import { reportsApi } from "@/api/reports";
import { formatBeijing } from "@/lib/datetime";

const projects = ref<Project[]>([]);
onMounted(async () => {
  const res = await projectsApi.list();
  projects.value = res;
});

async function downloadReport(p: Project) {
  await reportsApi.download(p.id, `${p.name}.xlsx`, p.selected_band ?? "P50");
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">报告中心</h1>
        <div class="page-sub">已计算项目的 Excel 报告导出入口</div>
      </div>
    </div>
    <div class="card" style="padding: 0">
      <table class="table">
        <thead><tr><th>项目</th><th>城市/行业</th><th>更新时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="p in projects" :key="p.id">
            <td><b>{{ p.name }}</b><div class="muted mono" style="font-size:11px">{{ p.id }}</div></td>
            <td>{{ p.city }} · {{ p.industry }}</td>
            <td class="muted mono" style="font-size:11px">{{ formatBeijing(p.updated_at) }}</td>
            <td><button class="btn btn-sm" @click="downloadReport(p)">下载 {{ p.selected_band ?? "P50" }} 报告</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
