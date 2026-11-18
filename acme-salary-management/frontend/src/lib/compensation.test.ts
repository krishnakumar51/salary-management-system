import { describe, expect, it } from "vitest";

import { calculateIncrement } from "@/lib/compensation";

describe("calculateIncrement", () => {
  it("matches the worked example: 10% of INR 1,500,000", () => {
    expect(calculateIncrement("1500000.00", "percentage", "10")).toEqual({
      newAmount: "1650000.00",
      incrementAmount: "150000.00",
      incrementPercentage: "10",
    });
  });

  it("applies a fixed amount and derives the percentage", () => {
    expect(calculateIncrement("1500000.00", "fixed", "75000")).toEqual({
      newAmount: "1575000.00",
      incrementAmount: "75000.00",
      incrementPercentage: "5",
    });
  });

  it("rounds half-up to cents and avoids float error", () => {
    // 10% of 100.05 = 10.005 -> 10.01 (a float implementation gives 10.00)
    expect(calculateIncrement("100.05", "percentage", "10")?.incrementAmount).toBe("10.01");
    // classic float trap: 0.1 + 0.2
    expect(calculateIncrement("0.10", "fixed", "0.20")?.newAmount).toBe("0.30");
  });

  it("handles fractional percentages and hourly-sized amounts", () => {
    expect(calculateIncrement("45.50", "percentage", "7.5")).toMatchObject({
      incrementAmount: "3.41", // 3.4125
      newAmount: "48.91",
    });
  });

  it("returns null for empty, zero, negative or non-numeric input", () => {
    for (const bad of ["", "0", "-5", "abc", "1e", "Infinity"]) {
      expect(calculateIncrement("1000", "percentage", bad)).toBeNull();
    }
    expect(calculateIncrement("not-a-number", "fixed", "5")).toBeNull();
  });
});
