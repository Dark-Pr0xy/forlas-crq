import { describe, expect, it } from "vitest";
import { formatCurrencyAUD, formatCurrencyAUDFull, fmt } from "@/lib/format";

describe("formatCurrencyAUD", () => {
  it.each([
    [0, "A$0"],
    [999, "A$999"],
    [1_000, "A$1.0K"],
    [30_800, "A$30.8K"],
    [100_000, "A$100K"],
    [320_000, "A$320K"],
    [1_000_000, "A$1.0M"],
    [10_000_000, "A$10.0M"],
    [100_000_000, "A$100.0M"],
    [1_000_000_000, "A$1.0B"],
    [12_500_000_000, "A$12.5B"],
  ])("formats %d as %s", (value, expected) => {
    expect(formatCurrencyAUD(value)).toBe(expected);
  });

  it("returns em dash for null / NaN", () => {
    expect(formatCurrencyAUD(null)).toBe("—");
    expect(formatCurrencyAUD(undefined)).toBe("—");
    expect(formatCurrencyAUD(Number.NaN)).toBe("—");
  });

  it("preserves the sign for negatives", () => {
    expect(formatCurrencyAUD(-30_800)).toBe("-A$30.8K");
  });

  it("never emits USD", () => {
    for (const v of [1, 1_000, 1_000_000, 1_000_000_000]) {
      const out = formatCurrencyAUD(v);
      expect(out).not.toContain("USD");
      expect(out.startsWith("A$")).toBe(true);
    }
  });
});

describe("formatCurrencyAUDFull", () => {
  it("uses a thousands separator", () => {
    expect(formatCurrencyAUDFull(1_250_000)).toBe("A$1,250,000");
    expect(formatCurrencyAUDFull(45_000)).toBe("A$45,000");
  });
});

describe("fmt helpers", () => {
  it("formats signed money", () => {
    expect(fmt.signedMoney(50_000)).toBe("+A$50.0K");
    expect(fmt.signedMoney(-50_000)).toBe("-A$50.0K");
  });
  it("formats sigma with sign", () => {
    expect(fmt.sigma(1.42)).toBe("+1.42σ");
    expect(fmt.sigma(-0.5)).toBe("-0.50σ");
  });
  it("formats percentages", () => {
    expect(fmt.pct(0.0821, 2)).toBe("8.21%");
  });
});
