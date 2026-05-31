import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import FpFormModal from "@/components/fp/FpFormModal.vue";

vi.mock("@/api/functions", () => ({
  functionsApi: { create: vi.fn().mockResolvedValue({}), patch: vi.fn().mockResolvedValue({}) },
}));

import { functionsApi } from "@/api/functions";
// Cast via unknown to avoid structural type mismatch with the real API type
const mockCreate = (functionsApi as unknown as { create: ReturnType<typeof vi.fn> }).create;

function mountModal(measurementMethod: string, editing: null = null) {
  return mount(FpFormModal, {
    props: { open: true, projectId: "p1", editing, measurementMethod },
  });
}

describe("FpFormModal — ifpug/nesma_detailed 方法", () => {
  beforeEach(() => { vi.clearAllMocks(); });
  it("渲染 DET / RET / FTR 输入", () => {
    const w = mountModal("ifpug");
    expect(w.find("[data-testid='input-det']").exists()).toBe(true);
    expect(w.find("[data-testid='input-ret']").exists()).toBe(true);
    expect(w.find("[data-testid='input-ftr']").exists()).toBe(true);
  });
  it("nesma_detailed 同样渲染 DET/RET/FTR", () => {
    const w = mountModal("nesma_detailed");
    expect(w.find("[data-testid='input-det']").exists()).toBe(true);
  });
});

describe("FpFormModal — nesma_estimated 方法", () => {
  beforeEach(() => { vi.clearAllMocks(); });
  it("不渲染 DET/RET/FTR", () => {
    const w = mountModal("nesma_estimated");
    expect(w.find("[data-testid='input-det']").exists()).toBe(false);
  });
  it("复杂度显示固定为 '中'", () => {
    const w = mountModal("nesma_estimated");
    expect(w.text()).toContain("中");
  });
});

describe("FpFormModal — nesma_indicative 方法", () => {
  beforeEach(() => { vi.clearAllMocks(); });
  it("category 仅渲染 ILF / EIF 选项", () => {
    const w = mountModal("nesma_indicative");
    const options = w.findAll("[data-testid='category-option']");
    const values = options.map((o) => o.attributes("value") ?? o.text().trim());
    expect(values).toContain("ILF");
    expect(values).toContain("EIF");
    expect(values).not.toContain("EI");
  });
});

describe("FpFormModal — cosmic 方法", () => {
  beforeEach(() => { vi.clearAllMocks(); });
  it("渲染 4 个数据移动输入", () => {
    const w = mountModal("cosmic");
    expect(w.find("[data-testid='input-cosmic-entry']").exists()).toBe(true);
    expect(w.find("[data-testid='input-cosmic-exit']").exists()).toBe(true);
    expect(w.find("[data-testid='input-cosmic-read']").exists()).toBe(true);
    expect(w.find("[data-testid='input-cosmic-write']").exists()).toBe(true);
  });
  it("实时显示 CFP = 入口 + 出口 + 读 + 写", async () => {
    const w = mountModal("cosmic");
    await w.find("[data-testid='input-cosmic-entry']").setValue("2");
    await w.find("[data-testid='input-cosmic-exit']").setValue("1");
    await w.find("[data-testid='input-cosmic-read']").setValue("3");
    await w.find("[data-testid='input-cosmic-write']").setValue("2");
    expect(w.find("[data-testid='cfp-total']").text()).toContain("8");
  });
  it("提交时 payload 含 cosmic_entry/exit/read/write", async () => {
    const w = mountModal("cosmic");
    await w.find("[data-testid='input-name']").setValue("登录");
    await w.find("[data-testid='input-cosmic-entry']").setValue("1");
    await w.find("[data-testid='input-cosmic-exit']").setValue("1");
    await w.find("[data-testid='input-cosmic-read']").setValue("1");
    await w.find("[data-testid='input-cosmic-write']").setValue("1");
    await w.find("form").trigger("submit");
    expect(mockCreate).toHaveBeenCalledWith(
      "p1",
      expect.objectContaining({
        cosmic_entry: 1, cosmic_exit: 1, cosmic_read: 1, cosmic_write: 1,
      }),
    );
  });
});
