import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import FpFormModal from "@/components/fp/FpFormModal.vue";
import { functionsApi } from "@/api/functions";

vi.mock("@/api/functions", () => ({
  functionsApi: { create: vi.fn().mockResolvedValue({}), patch: vi.fn() },
}));

describe("FpFormModal — IFPUG 复杂度联动", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it("ILF + DET 60 + RET 6 → 复杂度 high、UFP 15", async () => {
    const w = mount(FpFormModal, { props: { open: true, projectId: "p-1", measurementMethod: "ifpug" } });
    await flushPromises();
    await w.find("#fp-category").setValue("ILF");
    await w.find("#fp-det").setValue("60");
    await w.find("#fp-ret").setValue("6");
    await flushPromises();
    expect(w.text()).toContain("15");
    // 复杂度显示为「高」
    expect(w.find("[data-testid='fp-complexity-auto']").text()).toContain("高");
  });

  it("EI + DET 3 + FTR 1 → 复杂度 low、UFP 3", async () => {
    const w = mount(FpFormModal, { props: { open: true, projectId: "p-1", measurementMethod: "ifpug" } });
    await flushPromises();
    await w.find("#fp-category").setValue("EI");
    await w.find("#fp-det").setValue("3");
    await w.find("#fp-ftr").setValue("1");
    await flushPromises();
    expect(w.find("[data-testid='fp-complexity-auto']").text()).toContain("低");
    expect(w.text()).toContain("3");
  });

  it("ILF + DET 25 + RET 3 → average，提交 payload 含 det/ret", async () => {
    const w = mount(FpFormModal, { props: { open: true, projectId: "p-1", measurementMethod: "ifpug" } });
    await flushPromises();
    await w.find("#fp-name").setValue("查询客户");
    await w.find("#fp-category").setValue("ILF");
    await w.find("#fp-det").setValue("25");
    await w.find("#fp-ret").setValue("3");
    await w.find("form").trigger("submit");
    await flushPromises();
    expect(functionsApi.create).toHaveBeenCalledWith(
      "p-1",
      expect.objectContaining({ det: 25, ret: 3, category: "ILF" }),
    );
  });
});
