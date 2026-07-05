import { describe, expect, it } from "vitest";
import { interpolateY, returnPeriod } from "@/lib/interpolate";

describe("interpolateY", () => {
  const curve: [number, number][] = [
    [100, 1.0],
    [1_000, 0.5],
    [10_000, 0.1],
  ];

  it("clamps below the first point", () => {
    expect(interpolateY(curve, 10)).toBe(1.0);
  });

  it("clamps above the last point", () => {
    expect(interpolateY(curve, 1_000_000)).toBe(0.1);
  });

  it("returns exact values at the knots", () => {
    expect(interpolateY(curve, 1_000)).toBeCloseTo(0.5, 10);
  });

  it("interpolates in log-space between points", () => {
    // Geometric midpoint between 100 and 1000 is ~316; y should be halfway
    // between 1.0 and 0.5 = 0.75.
    expect(interpolateY(curve, Math.sqrt(100 * 1_000))).toBeCloseTo(0.75, 6);
  });

  it("handles empty data", () => {
    expect(interpolateY([], 5)).toBe(0);
  });
});

describe("returnPeriod", () => {
  it.each([
    [1, "every year"],
    [0.5, "1 in 2.0 years"],
    [0.1, "1 in 10 years"],
    [0.01, "1 in 100 years"],
    [0, "—"],
  ])("maps p=%s to %s", (p, expected) => {
    expect(returnPeriod(p)).toBe(expected);
  });

  it("gives a friendly label near p=1", () => {
    expect(returnPeriod(0.9)).toBe("~ once a year");
  });
});
