<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

function home(): void {
  router.replace({ name: "project-list" });
}
</script>

<template>
  <section
    class="page"
    aria-labelledby="title"
    role="alert"
  >
    <h1 id="title">
      页面不存在
    </h1>
    <p>请检查 URL，或返回项目列表重新进入。</p>
    <button
      type="button"
      class="btn btn-primary"
      @click="home"
    >
      返回项目列表
    </button>
  </section>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-6);
  max-width: 480px;
}
.page h1 {
  font-size: var(--font-size-lg);
  margin: 0;
}
.btn {
  align-self: flex-start;
}
</style>
