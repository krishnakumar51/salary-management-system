import Decimal from "decimal.js";

// Match the backend: Decimal arithmetic, ROUND_HALF_UP to cents. Never use JS floats for money.
Decimal.set({ rounding: Decimal.ROUND_HALF_UP, precision: 40 });

export interface IncrementResult {
  newAmount: string;
  incrementAmount: string;
  incrementPercentage: string;
}

/** Client-side preview of an increment. The server remains the source of truth. */
export function calculateIncrement(
  current: string,
  type: "percentage" | "fixed",
  value: string,
): IncrementResult | null {
  let cur: Decimal;
  let v: Decimal;
  try {
    cur = new Decimal(current);
    v = new Decimal(value);
  } catch {
    return null;
  }
  if (!v.isFinite() || v.lte(0)) return null;
  let increment: Decimal;
  let pct: Decimal;
  if (type === "percentage") {
    increment = cur.mul(v).div(100).toDecimalPlaces(2);
    pct = v;
  } else {
    increment = v.toDecimalPlaces(2);
    pct = cur.gt(0) ? increment.div(cur).mul(100).toDecimalPlaces(4) : new Decimal(0);
  }
  return {
    newAmount: cur.plus(increment).toFixed(2),
    incrementAmount: increment.toFixed(2),
    incrementPercentage: pct.toString(),
  };
}
