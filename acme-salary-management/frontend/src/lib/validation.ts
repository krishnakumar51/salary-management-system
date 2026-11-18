import type { Currency, EmployeeStatus, EmploymentType, Frequency } from "@/types/api";

export type Errors = Record<string, string>;

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const PHONE = /^\+?[0-9][0-9 ()-]{6,19}$/;
const MONEY = /^\d{1,12}(\.\d{1,2})?$/;

export interface EmployeeFormValues {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  country_id: string;
  department_id: string;
  designation: string;
  employment_type: EmploymentType;
  joining_date: string;
  status: EmployeeStatus;
  manager_id: string;
  // initial compensation (create only)
  amount: string;
  currency: Currency;
  frequency: Frequency;
}

export function validateEmployee(v: EmployeeFormValues, opts: { creating: boolean }): Errors {
  const e: Errors = {};
  if (!v.first_name.trim()) e.first_name = "First name is required";
  else if (v.first_name.length > 80) e.first_name = "Must be 80 characters or fewer";
  if (!v.last_name.trim()) e.last_name = "Last name is required";
  else if (v.last_name.length > 80) e.last_name = "Must be 80 characters or fewer";
  if (!v.email.trim()) e.email = "Email is required";
  else if (!EMAIL.test(v.email.trim())) e.email = "Enter a valid email address";
  if (v.phone.trim() && !PHONE.test(v.phone.trim())) e.phone = "Enter a valid phone number, e.g. +91 98765 43210";
  if (!v.country_id) e.country_id = "Select a country";
  if (!v.department_id) e.department_id = "Select a department";
  if (v.designation.trim().length < 2) e.designation = "Designation is required";
  if (!v.joining_date) e.joining_date = "Joining date is required";
  else {
    const max = new Date();
    max.setFullYear(max.getFullYear() + 1);
    if (v.joining_date < "1970-01-01") e.joining_date = "Date is too far in the past";
    else if (new Date(v.joining_date) > max) e.joining_date = "Cannot be more than a year in the future";
  }
  if (opts.creating && v.amount.trim() !== "" && !MONEY.test(v.amount.trim())) {
    e.amount = "Enter a non-negative amount with up to 2 decimals";
  }
  return e;
}

export interface IncrementFormValues {
  type: "percentage" | "fixed";
  value: string;
  effective_date: string;
  reason: string;
}

export function validateIncrement(v: IncrementFormValues, minDate?: string): Errors {
  const e: Errors = {};
  if (!v.value.trim()) e.value = "Enter a value";
  else if (!/^\d+(\.\d+)?$/.test(v.value.trim()) || Number(v.value) <= 0) e.value = "Must be a number greater than 0";
  else if (v.type === "percentage" && Number(v.value) > 1000) e.value = "Percentage cannot exceed 1000%";
  else if (v.type === "fixed" && !MONEY.test(v.value.trim())) e.value = "Use at most 2 decimal places";
  if (!v.effective_date) e.effective_date = "Effective date is required";
  else if (minDate && v.effective_date < minDate) {
    e.effective_date = `Cannot be before the current effective date (${minDate})`;
  }
  if (v.reason.trim().length < 3) e.reason = "Give a reason (at least 3 characters)";
  return e;
}

export interface CompensationFormValues {
  amount: string;
  currency: Currency;
  frequency: Frequency;
  effective_date: string;
  reason: string;
}

export function validateCompensation(v: CompensationFormValues, minDate?: string): Errors {
  const e: Errors = {};
  if (!v.amount.trim()) e.amount = "Enter an amount";
  else if (!MONEY.test(v.amount.trim())) e.amount = "Enter a non-negative amount with up to 2 decimals";
  if (!v.effective_date) e.effective_date = "Effective date is required";
  else if (minDate && v.effective_date < minDate) {
    e.effective_date = `Cannot be before the current effective date (${minDate})`;
  }
  if (v.reason.trim().length < 3) e.reason = "Give a reason (at least 3 characters)";
  return e;
}

export function hasErrors(e: Errors) {
  return Object.keys(e).length > 0;
}
