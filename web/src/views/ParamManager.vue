<script setup lang="ts">
defineProps<{ projectId: number }>();
</script>
<template>
  <div data-test="param-manager">
    参数管理（待实现）项目 #{{ projectId }}
  </div>
</template>
