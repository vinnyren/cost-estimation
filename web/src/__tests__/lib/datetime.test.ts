import { describe, it, expect } from "vitest";
import { formatBeijing, formatBeijingFull } from "@/lib/datetime";

describe("formatBeijing", () => {
  it("converts naive UTC timestamp to Beijing time (+8h)", () => {
    // 后端 naive UTC 07:10 → 北京时间 15:10
    expect(formatBeijing("2026-05-17T07:10:24")).toBe("2026-05-17 15:10");
  });

  it("handles UTC timestamp with Z suffix", () => {
    expect(formatBeijing("2026-05-17T07:10:24Z")).toBe("2026-05-17 15:10");
  });

  it("crosses day boundary correctly", () => {
    // UTC 20:00 + 8h → 次日 04:00
    expect(formatBeijing("2026-05-17T20:00:00")).toBe("2026-05-18 04:00");
  });

  it("returns dash for null/undefined/empty", () => {
    expect(formatBeijing(null)).toBe("—");
    expect(formatBeijing(undefined)).toBe("—");
    expect(formatBeijing("")).toBe("—");
  });

  it("returns input unchanged when unparseable", () => {
    expect(formatBeijing("not-a-date")).toBe("not-a-date");
  });
});

describe("formatBeijingFull", () => {
  it("includes seconds in Beijing time", () => {
    expect(formatBeijingFull("2026-05-17T07:10:24")).toBe("2026-05-17 15:10:24");
  });

  it("returns dash for null", () => {
    expect(formatBeijingFull(null)).toBe("—");
  });
});
