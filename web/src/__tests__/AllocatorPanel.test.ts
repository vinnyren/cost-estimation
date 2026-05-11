import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import AllocatorPanel from "@/components/result/AllocatorPanel.vue";

vi.mock("@/api/calc", () => ({
  calcApi: {
    allocate: vi.fn().mockResolvedValue({
      items: [
        { name: "前端", us: 50.5, locked: false, audit_tag: "budget_derived" },
        { name: "后端", us: 75.7, locked: false, audit_tag: "budget_derived" },
      ],
      validation: { recalc_total_us: 126.2, recalc_total_adjusted: 152.7, error_pct: 0.31 },
    }),
  },
}));

const stubReverseResult = {
  budget_for_dev: 1000000,
  budget_for_ops: 0,
  scale_adjusted_bands: { P10: 360.27, P50: 332.75, P90: 305.4 },
  scale_unadjusted_bands: { P10: 297.7, P50: 275, P90: 252.4 },
  scale_adjusted_ops_bands: { P10: 0, P50: 0, P90: 0 },
  scale_unadjusted_ops_bands: { P10: 0, P50: 0, P90: 0 },
  cf_used: 1.21,
  recommended_band: "P50" as const,
};

describe("AllocatorPanel", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it("renders 2 default draft rows", () => {
    const w = mount(AllocatorPanel, {
      props: { reverseResult: stubReverseResult, projectId: "p-1" },
    });
    expect(w.findAll(".allocator-drafts tbody tr")).toHaveLength(2);
  });

  it("adds and removes draft rows", async () => {
    const w = mount(AllocatorPanel, {
      props: { reverseResult: stubReverseResult, projectId: "p-1" },
    });
    await w.find(".allocator-actions .btn-ghost").trigger("click");
    expect(w.findAll(".allocator-drafts tbody tr")).toHaveLength(3);

    // remove the first row
    const removeBtn = w.findAll(".allocator-drafts tbody tr .btn")[0];
    await removeBtn.trigger("click");
    expect(w.findAll(".allocator-drafts tbody tr")).toHaveLength(2);
  });

  it("disables generate button when a draft has empty name", async () => {
    const w = mount(AllocatorPanel, {
      props: { reverseResult: stubReverseResult, projectId: "p-1" },
    });
    const nameInput = w.find(".allocator-drafts tbody tr input.field-input");
    await nameInput.setValue("   ");  // whitespace only
    const generateBtn = w.find(".btn-primary");
    expect((generateBtn.element as HTMLButtonElement).disabled).toBe(true);
  });

  it("emits allocated on successful generate", async () => {
    const w = mount(AllocatorPanel, {
      props: { reverseResult: stubReverseResult, projectId: "p-1" },
    });
    await w.find(".btn-primary").trigger("click");
    await new Promise((r) => setTimeout(r, 10));
    expect(w.emitted("allocated")).toBeTruthy();
    expect(w.emitted("allocated")?.[0][0]).toHaveProperty("items");
    expect(w.emitted("allocated")?.[0][0]).toHaveProperty("validation");
  });
});
