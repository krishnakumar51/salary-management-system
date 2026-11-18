import { ChevronLeft, ChevronRight, Info, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Select } from "@/components/ui/form";
import { formatDate, formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { RateInfo } from "@/types/api";

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        {description && <p className="mt-1 text-sm text-ink-soft">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  icon,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-ink-soft">{label}</p>
        {icon && <span className="text-ink-faint [&_svg]:size-4">{icon}</span>}
      </div>
      <p className="tabular mt-2 text-2xl font-semibold tracking-tight text-ink">{value}</p>
      {hint && <p className="mt-1 text-xs text-ink-faint">{hint}</p>}
    </Card>
  );
}

/** States exactly which exchange rates (and dates) back converted numbers. */
export function RateNote({ info, className }: { info?: RateInfo; className?: string }) {
  if (!info) return null;
  const parts = info.rates.map((r) => `1 ${r.from_currency} = ${Number(r.rate).toLocaleString("en-US", { maximumFractionDigits: 4 })} ${r.to_currency}`);
  return (
    <p className={cn("flex items-start gap-1.5 text-xs text-ink-faint", className)}>
      <Info className="mt-0.5 size-3.5 shrink-0" />
      <span>
        Converted to <strong className="font-medium text-ink-soft">{info.reporting_currency}</strong> using exchange rates
        {info.as_of ? ` effective ${formatDate(info.as_of)}` : ""}
        {parts.length ? ` (${parts.join(", ")})` : ""}. Stored salaries are unchanged.
      </span>
    </p>
  );
}

export function Pagination({
  page,
  pages,
  total,
  pageSize,
  onPage,
  onPageSize,
  pageSizes = [10, 25, 50, 100],
}: {
  page: number;
  pages: number;
  total: number;
  pageSize: number;
  onPage: (p: number) => void;
  onPageSize: (n: number) => void;
  pageSizes?: number[];
}) {
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-3 text-sm text-ink-soft">
      <div className="tabular" aria-live="polite">
        Showing <strong className="font-medium text-ink">{formatNumber(from)}</strong>–
        <strong className="font-medium text-ink">{formatNumber(to)}</strong> of{" "}
        <strong className="font-medium text-ink">{formatNumber(total)}</strong>
      </div>
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2">
          <span className="hidden sm:inline">Rows per page</span>
          <Select
            aria-label="Rows per page"
            className="h-8 w-[4.5rem] py-0"
            value={pageSize}
            onChange={(e) => onPageSize(Number(e.target.value))}
          >
            {pageSizes.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </Select>
        </label>
        <span className="tabular">
          Page {page} of {pages}
        </span>
        <div className="flex gap-1">
          <Button variant="secondary" size="icon" className="size-8" aria-label="Previous page" disabled={page <= 1} onClick={() => onPage(page - 1)}>
            <ChevronLeft />
          </Button>
          <Button variant="secondary" size="icon" className="size-8" aria-label="Next page" disabled={page >= pages} onClick={() => onPage(page + 1)}>
            <ChevronRight />
          </Button>
        </div>
      </div>
    </div>
  );
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  tone = "primary",
  busy,
  onConfirm,
  children,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  title: string;
  description?: string;
  confirmLabel: string;
  tone?: "primary" | "danger";
  busy?: boolean;
  onConfirm: () => void;
  children?: ReactNode;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title={title} description={description} className="max-w-md">
        {children}
        <DialogFooter className="mt-2">
          <Button variant="secondary" onClick={() => onOpenChange(false)} disabled={busy}>
            Cancel
          </Button>
          <Button variant={tone === "danger" ? "danger" : "primary"} onClick={onConfirm} disabled={busy}>
            {busy ? "Working…" : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function InlineAlert({ tone = "error", children }: { tone?: "error" | "warn" | "success"; children: ReactNode }) {
  const styles = {
    error: "border-bad/30 bg-bad-bg text-bad",
    warn: "border-warn/30 bg-warn-bg text-warn",
    success: "border-ok/30 bg-ok-bg text-ok",
  }[tone];
  return (
    <div role={tone === "error" ? "alert" : "status"} className={cn("flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm", styles)}>
      <TriangleAlert className="mt-0.5 size-4 shrink-0" />
      <div>{children}</div>
    </div>
  );
}
