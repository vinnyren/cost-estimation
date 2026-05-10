import { defineStore } from "pinia";
import { ref } from "vue";
import { projectsApi, type Project } from "@/api/projects";
import { ApiError } from "@/api/client";

export const useProjectsStore = defineStore("projects", () => {
  const items = ref<Project[]>([]);
  const state = ref<"idle" | "loading" | "success" | "error">("idle");
  const error = ref<ApiError | null>(null);

  async function fetchAll(): Promise<void> {
    state.value = "loading";
    error.value = null;
    try {
      const resp = await projectsApi.list();
      items.value = resp.items;
      state.value = "success";
    } catch (e) {
      error.value = e instanceof ApiError ? e : new ApiError("UNKNOWN", String(e));
      state.value = "error";
    }
  }

  async function create(body: Partial<Project>): Promise<Project> {
    const created = await projectsApi.create(body);
    items.value = [created, ...items.value];
    return created;
  }

  async function patch(id: string, body: Partial<Project>): Promise<void> {
    const updated = await projectsApi.patch(id, body);
    items.value = items.value.map((p) => (p.id === id ? updated : p));
  }

  async function remove(id: string): Promise<void> {
    await projectsApi.remove(id);
    items.value = items.value.filter((p) => p.id !== id);
  }

  return { items, state, error, fetchAll, create, patch, remove };
});
