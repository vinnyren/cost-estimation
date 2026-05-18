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

  it("新增模式：填写 name + 选 category + DET/RET → 提交 → create 被调用，payload 含 name/category/ufp", async () => {
    const w = mount(FpFormModal, {
      props: { open: true, projectId: "p-1", editing: null },
    });

    await w.find("#fp-name").setValue("新功能点");
    await w.find("#fp-category").setValue("ILF");
    // ILF DET=25 (band 1), RET=3 (band 1) → COMPLEXITY_MATRIX[1][1] = average → UFP 10
    await w.find("#fp-det").setValue("25");
    await w.find("#fp-ret").setValue("3");
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

  it("UFP 自动计算：选 ILF + DET 60 + RET 6 → 复杂度 high → 显示 15", async () => {
    const w = mount(FpFormModal, {
      props: { open: true, projectId: "p-1", editing: null },
    });

    await w.find("#fp-category").setValue("ILF");
    // ILF DET=60 (band 2), RET=6 (band 2) → COMPLEXITY_MATRIX[2][2] = high → UFP 15
    await w.find("#fp-det").setValue("60");
    await w.find("#fp-ret").setValue("6");
    await flushPromises();

    const ufpDisplay = w.find("[data-testid='fp-ufp-auto']");
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

  it("UFP 表默认值 EI + 无 DET/FTR → 复杂度 average → UFP 4", async () => {
    const w = mount(FpFormModal, {
      props: { open: true, projectId: "p-1", editing: null },
    });

    // default: category=EI, det/ftr=null → complexity=average → UFP=4
    const ufpDisplay = w.find("[data-testid='fp-ufp-auto']");
    expect(ufpDisplay.text()).toBe("4");
  });

  it("不渲染口径选择器（运维不是独立的功能点清单）", async () => {
    const w = mount(FpFormModal, {
      props: { open: true, projectId: "p-1", editing: null },
    });
    expect(w.find("#fp-kind").exists()).toBe(false);
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
