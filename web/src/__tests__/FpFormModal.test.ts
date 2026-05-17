import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import FpFormModal from "@/components/fp/FpFormModal.vue";
import type { FunctionPoint } from "@/api/functions";

vi.mock("@/api/functions", () => ({
  functionsApi: {
    create: vi.fn(),
    patch: vi.fn(),
    remove: vi.fn(),
    list: vi.fn(),
    bulk: vi.fn(),
    snapshots: vi.fn(),
    restore: vi.fn(),
  },
}));

import { functionsApi } from "@/api/functions";

const mockFp: FunctionPoint = {
  id: "fp-001",
  project_id: "p-1",
  name: "用户登录",
  description: "用户通过账号密码登录系统",
  subsystem: "认证中心",
  l1_module: "登录模块",
  l2_module: "密码验证",
  category: "EI",
  complexity: "low",
  ufp: 3,
  us: 3,
  source: "manual",
  version: 1,
};

describe("FpFormModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (functionsApi.create as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...mockFp,
      id: "fp-new",
    });
    (functionsApi.patch as ReturnType<typeof vi.fn>).mockResolvedValue(mockFp);
  });

  it("新增模式：填写 name + 选 category/complexity → 提交 → create 被调用，payload 含 name/category/ufp", async () => {
    const w = mount(FpFormModal, {
      props: { open: true, projectId: "p-1", editing: null },
    });

    await w.find("#fp-name").setValue("新功能点");
    await w.find("#fp-category").setValue("ILF");
    await w.find("#fp-complexity").setValue("average");
    await w.find("form").trigger("submit");
    await flushPromises();

    expect(functionsApi.create).toHaveBeenCalledOnce();
    const payload = (functionsApi.create as ReturnType<typeof vi.fn>).mock.calls[0][1];
    expect(payload.name).toBe("新功能点");
    expect(payload.category).toBe("ILF");
    expect(payload.ufp).toBe(10); // ILF average = 10
    expect(payload.us).toBe(10);
    expect(payload.source).toBe("manual");
  });

  it("UFP 自动计算：选 ILF + high → 显示 15", async () => {
    const w = mount(FpFormModal, {
      props: { open: true, projectId: "p-1", editing: null },
    });

    await w.find("#fp-category").setValue("ILF");
    await w.find("#fp-complexity").setValue("high");
    await flushPromises();

    const ufpDisplay = w.find(".ufp-value");
    expect(ufpDisplay.exists()).toBe(true);
    expect(ufpDisplay.text()).toBe("15");
  });

  it("name 为空提交 → 不调 create，显示必填提示", async () => {
    const w = mount(FpFormModal, {
      props: { open: true, projectId: "p-1", editing: null },
    });

    // name 保持空，直接提交
    await w.find("form").trigger("submit");
    await flushPromises();

    expect(functionsApi.create).not.toHaveBeenCalled();
    expect(w.text()).toContain("功能点名称必填");
  });

  it("编辑模式：传 editing prop → 表单预填该 FP 的 name", async () => {
    const w = mount(FpFormModal, {
      props: { open: true, projectId: "p-1", editing: mockFp },
    });
    await flushPromises();

    const nameInput = w.find("#fp-name").element as HTMLInputElement;
    expect(nameInput.value).toBe("用户登录");
  });

  it("编辑模式提交 → 调 patch 而非 create，payload 不含 source", async () => {
    const w = mount(FpFormModal, {
      props: { open: true, projectId: "p-1", editing: mockFp },
    });
    await flushPromises();

    await w.find("form").trigger("submit");
    await flushPromises();

    expect(functionsApi.patch).toHaveBeenCalledOnce();
    expect(functionsApi.create).not.toHaveBeenCalled();
    const payload = (functionsApi.patch as ReturnType<typeof vi.fn>).mock.calls[0][2];
    expect(payload.source).toBeUndefined();
  });

  it("UFP 表默认值 EI + low = 3", async () => {
    const w = mount(FpFormModal, {
      props: { open: true, projectId: "p-1", editing: null },
    });

    // default: category=EI, complexity=low
    const ufpDisplay = w.find(".ufp-value");
    expect(ufpDisplay.text()).toBe("3");
  });

  it("新增模式默认口径 dev，可选运维 → payload.fp_kind 为 ops", async () => {
    const w = mount(FpFormModal, {
      props: { open: true, projectId: "p-1", editing: null },
    });

    const kindSelect = w.find("#fp-kind");
    expect(kindSelect.exists()).toBe(true);
    expect((kindSelect.element as HTMLSelectElement).value).toBe("dev");

    await w.find("#fp-name").setValue("运维功能点");
    await kindSelect.setValue("ops");
    await w.find("form").trigger("submit");
    await flushPromises();

    expect(functionsApi.create).toHaveBeenCalledOnce();
    const payload = (functionsApi.create as ReturnType<typeof vi.fn>).mock.calls[0][1];
    expect(payload.fp_kind).toBe("ops");
  });

  it("编辑模式预填 fp_kind（ops FP 预填为运维）", async () => {
    const w = mount(FpFormModal, {
      props: {
        open: true,
        projectId: "p-1",
        editing: { ...mockFp, fp_kind: "ops" },
      },
    });
    await flushPromises();

    const kindSelect = w.find("#fp-kind").element as HTMLSelectElement;
    expect(kindSelect.value).toBe("ops");
  });

  it("API 失败时显示错误 banner", async () => {
    (functionsApi.create as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("服务器错误"),
    );

    const w = mount(FpFormModal, {
      props: { open: true, projectId: "p-1", editing: null },
    });

    await w.find("#fp-name").setValue("测试功能点");
    await w.find("form").trigger("submit");
    await flushPromises();

    expect(w.text()).toContain("服务器错误");
  });
});
