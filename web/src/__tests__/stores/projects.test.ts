import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useProjectsStore } from "@/stores/projects";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    list: vi.fn().mockResolvedValue([
      {
        id: "p-1",
        name: "p1",
        project_type: "dev_only",
        mode: "forward",
        city: "北京",
        industry: "电子政务",
        phase: "bidding",
        basis_data_ver: "CSBMK®-202510",
        created_at: "",
        updated_at: "",
      },
    ]),
    create: vi.fn().mockResolvedValue({
      id: "p-2",
      name: "p2",
      project_type: "dev_only",
      mode: "reverse",
      city: "上海",
      industry: "金融",
      phase: "budget",
      basis_data_ver: "CSBMK®-202510",
      created_at: "",
      updated_at: "",
    }),
    patch: vi.fn().mockResolvedValue({
      id: "p-1",
      name: "p1-renamed",
      project_type: "dev_only",
      mode: "forward",
      city: "北京",
      industry: "电子政务",
      phase: "bidding",
      basis_data_ver: "CSBMK®-202510",
      created_at: "",
      updated_at: "",
    }),
    remove: vi.fn().mockResolvedValue(undefined),
  },
}));

describe("projectsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("fetchAll 写入 items", async () => {
    const store = useProjectsStore();
    await store.fetchAll();
    expect(store.items).toHaveLength(1);
    expect(store.state).toBe("success");
  });

  it("create 追加 item", async () => {
    const store = useProjectsStore();
    await store.fetchAll();
    await store.create({
      name: "p2",
      project_type: "dev_only",
      mode: "reverse",
      city: "上海",
      industry: "金融",
      phase: "budget",
      basis_data_ver: "CSBMK®-202510",
    });
    expect(store.items).toHaveLength(2);
  });

  it("remove 移除 item", async () => {
    const store = useProjectsStore();
    await store.fetchAll();
    await store.remove("p-1");
    expect(store.items).toHaveLength(0);
  });

  it("patch 更新对应 item", async () => {
    const store = useProjectsStore();
    await store.fetchAll();
    await store.patch("p-1", { name: "p1-renamed" });
    expect(store.items[0].name).toBe("p1-renamed");
  });

  it("fetchAll 失败 → state=error 且 error 暴露 ApiError", async () => {
    const projectsModule = await import("@/api/projects");
    (projectsModule.projectsApi.list as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("网络错"),
    );
    const store = useProjectsStore();
    await store.fetchAll();
    expect(store.state).toBe("error");
    expect(store.error).not.toBeNull();
    expect(store.error?.message).toContain("网络错");
  });
});
