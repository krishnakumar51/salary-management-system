import type { Currency, EmployeeStatus, EmploymentType, Frequency } from "@/types/api";

const LOCALE: Record<Currency, string> = { INR: "en-IN", USD: "en-US", EUR: "de-DE" };

/** Display-only formatting. Arithmetic never goes through here. */
export function formatMoney(
  amount: string | number,
  currency: Currency,
  opts: { compact?: boolean; decimals?: number } = {},
) {
  const n = typeof amount === "string" ? Number(amount) : amount;
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat(LOCALE[currency], {
    style: "currency",
    currency,
    notation: opts.compact ? "compact" : "standard",
    minimumFractionDigits: opts.compact ? 0 : (opts.decimals ?? 0),
    maximumFractionDigits: opts.compact ? 1 : (opts.decimals ?? 2),
  }).format(n);
}

export const FREQUENCY_LABEL: Record<Frequency, string> = {
  annual: "per year",
  monthly: "per month",
  hourly: "per hour",
};
export const FREQUENCY_SHORT: Record<Frequency, string> = { annual: "/yr", monthly: "/mo", hourly: "/hr" };

export function formatPay(amount: string, currency: Currency, frequency: Frequency) {
  // hourly rates need cents; others round to whole units for scanability
  return `${formatMoney(amount, currency, { decimals: frequency === "hourly" ? 2 : 0 })} ${FREQUENCY_SHORT[frequency]}`;
}

export function formatDate(iso: string | null | undefined) {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatNumber(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}

export const STATUS_LABEL: Record<EmployeeStatus, string> = {
  active: "Active",
  on_leave: "On leave",
  terminated: "Terminated",
};
export const EMPLOYMENT_LABEL: Record<EmploymentType, string> = {
  full_time: "Full-time",
  part_time: "Part-time",
  contract: "Contract",
  intern: "Intern",
};
export const CHANGE_LABEL: Record<string, string> = {
  initial: "Initial compensation",
  set: "Salary updated",
  fixed_increment: "Fixed increment",
  percentage_increment: "Percentage increment",
};
export const CURRENCY_LIST: Currency[] = ["INR", "USD", "EUR"];

export function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
