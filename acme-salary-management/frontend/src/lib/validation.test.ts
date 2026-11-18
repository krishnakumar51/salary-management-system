import { describe, expect, it } from "vitest";

import {
  hasErrors,
  validateCompensation,
  validateEmployee,
  validateIncrement,
  type EmployeeFormValues,
} from "@/lib/validation";

const valid: EmployeeFormValues = {
  first_name: "Aarav",
  last_name: "Sharma",
  email: "aarav@acme-demo.com",
  phone: "+91 98765 43210",
  country_id: "1",
  department_id: "2",
  designation: "Software Engineer",
  employment_type: "full_time",
  joining_date: "2023-04-01",
  status: "active",
  manager_id: "",
  amount: "1500000",
  currency: "INR",
  frequency: "annual",
};

describe("validateEmployee", () => {
  it("accepts a complete record", () => {
    expect(validateEmployee(valid, { creating: true })).toEqual({});
  });

  it("flags every missing required field with a readable message", () => {
    const errs = validateEmployee(
      { ...valid, first_name: " ", last_name: "", email: "", country_id: "", department_id: "", designation: "", joining_date: "" },
      { creating: true },
    );
    expect(Object.keys(errs).sort()).toEqual(
      ["country_id", "department_id", "designation", "email", "first_name", "joining_date", "last_name"],
    );
    expect(errs.email).toBe("Email is required");
  });

  it.each(["plain", "a@b", "a b@c.com", "@c.com"])("rejects malformed email %s", (email) => {
    expect(validateEmployee({ ...valid, email }, { creating: false }).email).toMatch(/valid email/i);
  });

  it("validates phone only when provided", () => {
    expect(validateEmployee({ ...valid, phone: "" }, { creating: false }).phone).toBeUndefined();
    expect(validateEmployee({ ...valid, phone: "abc" }, { creating: false }).phone).toMatch(/valid phone/i);
  });

  it("rejects absurd joining dates", () => {
    expect(validateEmployee({ ...valid, joining_date: "1950-01-01" }, { creating: false }).joining_date).toMatch(/past/i);
    expect(validateEmployee({ ...valid, joining_date: "2999-01-01" }, { creating: false }).joining_date).toMatch(/future/i);
  });

  it("validates the optional starting salary only when creating", () => {
    for (const amount of ["-5", "10.123", "abc", "1,000"]) {
      expect(validateEmployee({ ...valid, amount }, { creating: true }).amount).toBeDefined();
    }
    expect(validateEmployee({ ...valid, amount: "" }, { creating: true }).amount).toBeUndefined();
    expect(validateEmployee({ ...valid, amount: "-5" }, { creating: false }).amount).toBeUndefined();
  });
});

describe("validateIncrement", () => {
  const base = { type: "percentage" as const, value: "10", effective_date: "2024-05-01", reason: "Annual review" };

  it("accepts a valid increment", () => {
    expect(hasErrors(validateIncrement(base, "2024-01-01"))).toBe(false);
  });

  it.each(["", "0", "-3", "abc"])("rejects value %j", (value) => {
    expect(validateIncrement({ ...base, value }).value).toBeDefined();
  });

  it("caps percentages at 1000% and limits fixed amounts to 2 decimals", () => {
    expect(validateIncrement({ ...base, value: "1001" }).value).toMatch(/1000/);
    expect(validateIncrement({ ...base, type: "fixed", value: "10.555" }).value).toMatch(/2 decimal/);
  });

  it("requires a reason and an effective date not before the current one", () => {
    expect(validateIncrement({ ...base, reason: "ab" }).reason).toBeDefined();
    expect(validateIncrement({ ...base, effective_date: "" }).effective_date).toBeDefined();
    expect(validateIncrement({ ...base, effective_date: "2023-12-31" }, "2024-01-01").effective_date).toMatch(/before/i);
  });
});

describe("validateCompensation", () => {
  it("requires a non-negative amount with at most 2 decimals", () => {
    const base = { amount: "1000", currency: "USD" as const, frequency: "annual" as const, effective_date: "2024-01-01", reason: "Market" };
    expect(hasErrors(validateCompensation(base))).toBe(false);
    expect(validateCompensation({ ...base, amount: "" }).amount).toBeDefined();
    expect(validateCompensation({ ...base, amount: "-1" }).amount).toBeDefined();
    expect(validateCompensation({ ...base, amount: "1.234" }).amount).toBeDefined();
  });
});
