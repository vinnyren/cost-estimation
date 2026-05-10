import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useProjectsStore } from "@/stores/projects";

vi.mock("@/api/projects", () => ({
  projectsApi: {
    list: vi.fn().mockResolvedValue({
      items: [
        {
          id: 1,
          name: "p1",
          mode: "forward",
          city: "北京",
          industry: "电子政务",
          stage: "bidding",
          created_at: "",
          updated_at: "",
        },
      ],
    }),
    create: vi.fn().mockResolvedValue({
      id: 2,
      name: "p2",
      mode: "reverse",
      city: "上海",
      industry: "金融",
      stage: "budget",
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
      mode: "reverse",
      city: "上海",
      industry: "金融",
      stage: "budget",
    });
    expect(store.items).toHaveLength(2);
  });

  it("remove 移除 item", async () => {
    const store = useProjectsStore();
    await store.fetchAll();
    await store.remove(1);
    expect(store.items).toHaveLength(0);
  });
});
