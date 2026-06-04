import { describe, it, expect } from "vitest";
import { qualityKey } from "./quality";

describe("qualityKey relative bucketing", () => {
  it("top suggestion is always High", () => {
    for (const n of [1, 2, 3, 5, 6, 9, 20]) {
      expect(qualityKey(0, n)).toBe("high");
    }
  });

  it("bottom suggestion is always Lower for 3+ results", () => {
    for (const n of [3, 5, 6, 9, 20]) {
      expect(qualityKey(n - 1, n)).toBe("lower");
    }
  });

  it("with only 1-2 results, all show High", () => {
    expect(qualityKey(0, 1)).toBe("high");
    expect(qualityKey(0, 2)).toBe("high");
    expect(qualityKey(1, 2)).toBe("high");
  });

  it("splits a list of 6 into high/medium/lower thirds", () => {
    const buckets = [0, 1, 2, 3, 4, 5].map((i) => qualityKey(i, 6));
    expect(buckets).toEqual(["high", "high", "medium", "medium", "lower", "lower"]);
  });

  it("splits a list of 3 into one each", () => {
    expect([0, 1, 2].map((i) => qualityKey(i, 3))).toEqual(["high", "medium", "lower"]);
  });
});
