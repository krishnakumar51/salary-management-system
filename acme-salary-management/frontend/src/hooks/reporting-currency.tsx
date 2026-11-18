import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import type { Currency } from "@/types/api";

const KEY = "acme.reportingCurrency";
const VALID: Currency[] = ["INR", "USD", "EUR"];

function initial(): Currency {
  try {
    const stored = localStorage.getItem(KEY) as Currency | null;
    if (stored && VALID.includes(stored)) return stored;
  } catch {
    /* storage unavailable */
  }
  return "USD";
}

interface ReportingCurrencyState {
  currency: Currency;
  setCurrency: (c: Currency) => void;
}
const Ctx = createContext<ReportingCurrencyState | null>(null);

/** The consolidated-reporting currency. Display/analytics only: stored salaries are never converted in place. */
export function ReportingCurrencyProvider({ children, initialCurrency }: { children: ReactNode; initialCurrency?: Currency }) {
  const [currency, set] = useState<Currency>(initialCurrency ?? initial());
  const setCurrency = useCallback((c: Currency) => {
    set(c);
    try {
      localStorage.setItem(KEY, c);
    } catch {
      /* ignore */
    }
  }, []);
  const value = useMemo(() => ({ currency, setCurrency }), [currency, setCurrency]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useReportingCurrency(): ReportingCurrencyState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useReportingCurrency must be used inside <ReportingCurrencyProvider>");
  return ctx;
}
