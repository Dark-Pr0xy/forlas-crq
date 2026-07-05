import { describe, expect, it } from "vitest";
import { stableStringify } from "@/lib/stableStringify";

describe("stableStringify", () => {
  it("is insensitive to key order", () => {
    const a = { name: "x", tolerance: 5, inputs: { tef: { min: 1, max: 3 } } };
    const b = { inputs: { tef: { max: 3, min: 1 } }, tolerance: 5, name: "x" };
    expect(stableStringify(a)).toBe(stableStringify(b));
  });

  it("distinguishes different values", () => {
    const a = { tolerance: 5 };
    const b = { tolerance: 6 };
    expect(stableStringify(a)).not.toBe(stableStringify(b));
  });

  it("preserves array order", () => {
    expect(stableStringify([3, 1, 2])).not.toBe(stableStringify([1, 2, 3]));
  });

  it("handles nested arrays of objects", () => {
    const a = { lines: [{ label: "P50", value: 1 }] };
    const b = { lines: [{ value: 1, label: "P50" }] };
    expect(stableStringify(a)).toBe(stableStringify(b));
  });
});
