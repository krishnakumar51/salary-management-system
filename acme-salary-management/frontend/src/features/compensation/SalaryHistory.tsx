import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";

import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { CHANGE_LABEL, formatDate, formatDateTime, formatPay } from "@/lib/format";
import { employeesApi } from "@/services/endpoints";
import type { SalaryHistoryEntry } from "@/types/api";

function Entry({ h }: { h: SalaryHistoryEntry }) {
  const currencyChanged = h.previous_currency && h.previous_currency !== h.new_currency;
  const pct = h.increment_percentage ? Number(h.increment_percentage) : null;
  return (
    <li className="relative pl-8">
      <span className="absolute left-0 top-1.5 grid size-5 place-items-center rounded-full bg-brand-50 ring-4 ring-surface">
        <span className="size-2 rounded-full bg-brand-600" />
      </span>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="text-sm font-medium text-ink">{CHANGE_LABEL[h.change_type] ?? h.change_type}</span>
        {pct !== null && <Badge tone="ok">+{pct.toLocaleString("en-US", { maximumFractionDigits: 2 })}%</Badge>}
        {currencyChanged && <Badge tone="warn">Currency changed</Badge>}
        <span className="text-xs text-ink-faint">Effective {formatDate(h.effective_date)}</span>
      </div>
      <div className="tabular mt-1 flex flex-wrap items-center gap-2 text-sm">
        {h.previous_amount !== null && h.previous_currency && h.previous_frequency ? (
          <>
            <span className="text-ink-soft">{formatPay(h.previous_amount, h.previous_currency, h.previous_frequency)}</span>
            <ArrowRight className="size-3.5 text-ink-faint" />
          </>
        ) : null}
        <span className="font-semibold text-ink">{formatPay(h.new_amount, h.new_currency, h.new_frequency)}</span>
      </div>
      <p className="mt-1 text-sm text-ink-soft">{h.reason}</p>
      <p className="mt-0.5 text-xs text-ink-faint">
        Recorded {formatDateTime(h.created_at)}
        {h.changed_by_name ? ` by ${h.changed_by_name}` : ""}
      </p>
    </li>
  );
}

export function SalaryHistory({ employeeId }: { employeeId: number }) {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["salary-history", employeeId],
    queryFn: () => employeesApi.history(employeeId),
  });
  if (isLoading) return <LoadingState label="Loading salary history…" />;
  if (isError) return <ErrorState error={error} onRetry={() => refetch()} title="Couldn't load salary history" />;
  if (!data || data.length === 0) {
    return <EmptyState title="No salary history yet" description="Changes will appear here as soon as compensation is recorded." />;
  }
  // API returns oldest → newest; show the most recent change first.
  const entries = [...data].reverse();
  return (
    <ol aria-label="Salary history" className="relative space-y-6 before:absolute before:left-[9px] before:top-2 before:h-[calc(100%-1rem)] before:w-px before:bg-line">
      {entries.map((h) => (
        <Entry key={h.id} h={h} />
      ))}
    </ol>
  );
}
