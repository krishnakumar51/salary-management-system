import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";

import { InlineAlert } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field, Input, Textarea } from "@/components/ui/form";
import { calculateIncrement } from "@/lib/compensation";
import { formatMoney, FREQUENCY_LABEL, todayIso } from "@/lib/format";
import { hasErrors, validateIncrement, type Errors } from "@/lib/validation";
import { ApiError } from "@/services/api";
import { compensationApi } from "@/services/endpoints";
import type { Compensation } from "@/types/api";

export function IncrementDialog({
  compensation,
  employeeName,
  open,
  onOpenChange,
}: {
  compensation: Compensation;
  employeeName: string;
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const qc = useQueryClient();
  const [type, setType] = useState<"percentage" | "fixed">("percentage");
  const [value, setValue] = useState("");
  const [date, setDate] = useState(todayIso() < compensation.effective_date ? compensation.effective_date : todayIso());
  const [reason, setReason] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const [reviewing, setReviewing] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const preview = useMemo(() => calculateIncrement(compensation.amount, type, value), [compensation.amount, type, value]);
  const { currency, frequency } = compensation;
  const money = (v: string) => formatMoney(v, currency, { decimals: 2 });

  const mutation = useMutation({
    mutationFn: () => compensationApi.increment(compensation.id, { type, value: value.trim(), effective_date: date, reason: reason.trim() }),
    onSuccess: async () => {
      await qc.invalidateQueries();
      onOpenChange(false);
    },
    onError: (err) => {
      setServerError(err instanceof ApiError ? err.message : "Could not apply the increment.");
      setReviewing(false);
      if (err instanceof ApiError) setErrors({ ...err.fieldErrors() });
    },
  });

  const review = (e: FormEvent) => {
    e.preventDefault();
    const errs = validateIncrement({ type, value, effective_date: date, reason }, compensation.effective_date);
    setErrors(errs);
    setServerError(null);
    if (!hasErrors(errs)) setReviewing(true);
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !mutation.isPending && onOpenChange(o)}>
      <DialogContent
        title={reviewing ? "Confirm salary increment" : "Apply increment"}
        description={
          reviewing
            ? `This permanently records a salary change for ${employeeName}.`
            : `${employeeName} · currently ${money(compensation.amount)} ${FREQUENCY_LABEL[frequency]}`
        }
      >
        {reviewing && preview ? (
          <div>
            <div className="rounded-lg border border-line bg-canvas p-4">
              <div className="flex flex-wrap items-center gap-3 text-lg font-semibold tabular">
                <span className="text-ink-soft">{money(compensation.amount)}</span>
                <ArrowRight className="size-4 text-ink-faint" />
                <span className="text-ink">{money(preview.newAmount)}</span>
              </div>
              <p className="mt-2 text-sm text-ink-soft">
                +{money(preview.incrementAmount)} ({Number(preview.incrementPercentage).toLocaleString("en-US", { maximumFractionDigits: 4 })}%) {FREQUENCY_LABEL[frequency]} ·
                effective {date}
              </p>
              <p className="mt-1 text-sm text-ink-soft">Reason: {reason.trim()}</p>
            </div>
            {serverError && <div className="mt-3"><InlineAlert>{serverError}</InlineAlert></div>}
            <DialogFooter>
              <Button variant="secondary" onClick={() => setReviewing(false)} disabled={mutation.isPending}>
                Back
              </Button>
              <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
                {mutation.isPending ? "Applying…" : "Confirm increment"}
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={review} noValidate className="space-y-4">
            {serverError && <InlineAlert>{serverError}</InlineAlert>}
            <fieldset>
              <legend className="mb-1.5 text-sm font-medium text-ink">Increment type</legend>
              <div className="grid grid-cols-2 gap-2 rounded-lg bg-canvas p-1" role="radiogroup" aria-label="Increment type">
                {(["percentage", "fixed"] as const).map((t) => (
                  <button
                    key={t}
                    type="button"
                    role="radio"
                    aria-checked={type === t}
                    onClick={() => setType(t)}
                    className={`rounded-md px-3 py-1.5 text-sm font-medium ${type === t ? "bg-surface text-ink shadow-card" : "text-ink-soft"}`}
                  >
                    {t === "percentage" ? "Percentage (%)" : `Fixed amount (${currency})`}
                  </button>
                ))}
              </div>
            </fieldset>
            <Field id="inc-value" label={type === "percentage" ? "Increment percentage" : `Increment amount (${currency})`} error={errors.value} required>
              {(p) => (
                <Input {...p} inputMode="decimal" placeholder={type === "percentage" ? "e.g. 10" : "e.g. 50000"} value={value} onChange={(e) => setValue(e.target.value)} />
              )}
            </Field>

            <div aria-live="polite" className="rounded-lg border border-line bg-canvas px-4 py-3 text-sm">
              {preview ? (
                <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                  <dt className="text-ink-soft">Increment</dt>
                  <dd className="tabular text-right font-medium">
                    {money(preview.incrementAmount)} ({Number(preview.incrementPercentage).toLocaleString("en-US", { maximumFractionDigits: 4 })}%)
                  </dd>
                  <dt className="text-ink-soft">New salary</dt>
                  <dd data-testid="new-salary" className="tabular text-right text-base font-semibold text-ink">
                    {money(preview.newAmount)}
                  </dd>
                </dl>
              ) : (
                <p className="text-ink-faint">Enter a value to preview the new salary.</p>
              )}
            </div>

            <Field id="inc-date" label="Effective date" error={errors.effective_date} required>
              {(p) => <Input {...p} type="date" min={compensation.effective_date} value={date} onChange={(e) => setDate(e.target.value)} />}
            </Field>
            <Field id="inc-reason" label="Reason" error={errors.reason} required>
              {(p) => <Textarea {...p} rows={2} maxLength={500} placeholder="e.g. Annual performance review" value={reason} onChange={(e) => setReason(e.target.value)} />}
            </Field>
            <DialogFooter>
              <Button variant="secondary" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit">Review increment</Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
