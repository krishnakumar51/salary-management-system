import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { useState, type FormEvent } from "react";

import { InlineAlert } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/form";
import { CURRENCY_LIST, formatPay, todayIso } from "@/lib/format";
import { hasErrors, validateCompensation, type Errors } from "@/lib/validation";
import { ApiError } from "@/services/api";
import { compensationApi, ratesApi } from "@/services/endpoints";
import type { Compensation, Currency, Frequency } from "@/types/api";

/**
 * One dialog for both cases:
 *  - `existing` given  -> update salary / currency / frequency (PATCH, recorded in salary history)
 *  - `employee` only   -> add the first compensation record (POST)
 */
export function CompensationDialog({
  open,
  onOpenChange,
  employee,
  existing,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  employee: { id: number; name: string; defaultCurrency: Currency; joiningDate: string };
  existing?: Compensation | null;
}) {
  const qc = useQueryClient();
  const creating = !existing;
  const minDate = existing?.effective_date;
  const [amount, setAmount] = useState(existing?.amount ?? "");
  const [currency, setCurrency] = useState<Currency>(existing?.currency ?? employee.defaultCurrency);
  const [frequency, setFrequency] = useState<Frequency>(existing?.frequency ?? "annual");
  const initialDate = creating ? (employee.joiningDate > todayIso() ? employee.joiningDate : todayIso()) : todayIso() < (minDate ?? "") ? minDate! : todayIso();
  const [date, setDate] = useState(initialDate);
  const [reason, setReason] = useState(creating ? "Initial compensation" : "");
  const [errors, setErrors] = useState<Errors>({});
  const [reviewing, setReviewing] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [convertNote, setConvertNote] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      existing
        ? compensationApi.update(existing.id, { amount: amount.trim(), currency, frequency, effective_date: date, reason: reason.trim() })
        : compensationApi.create({ employee_id: employee.id, amount: amount.trim(), currency, frequency, effective_date: date, reason: reason.trim() }),
    onSuccess: async () => {
      await qc.invalidateQueries();
      onOpenChange(false);
    },
    onError: (err) => {
      setServerError(err instanceof ApiError ? err.message : "Could not save compensation.");
      setReviewing(false);
      if (err instanceof ApiError) setErrors(err.fieldErrors());
    },
  });

  const convert = useMutation({
    mutationFn: () => ratesApi.convert(existing!.amount, existing!.currency, currency),
    onSuccess: (res) => {
      setAmount(res.converted);
      setConvertNote(`Converted ${existing!.currency} → ${currency} at ${Number(res.rate).toLocaleString("en-US", { maximumFractionDigits: 6 })} (rate effective ${res.effective_date ?? "today"}). Adjust if needed.`);
    },
    onError: (err) => setServerError(err instanceof ApiError ? err.message : "Conversion failed."),
  });

  const review = (e: FormEvent) => {
    e.preventDefault();
    const errs = validateCompensation({ amount, currency, frequency, effective_date: date, reason }, minDate);
    setErrors(errs);
    setServerError(null);
    if (!hasErrors(errs)) setReviewing(true);
  };

  const currencyChanged = existing && currency !== existing.currency;

  return (
    <Dialog open={open} onOpenChange={(o) => !mutation.isPending && onOpenChange(o)}>
      <DialogContent
        title={reviewing ? "Confirm salary change" : creating ? "Add compensation" : "Update compensation"}
        description={reviewing ? `This permanently records a salary change for ${employee.name}.` : employee.name}
      >
        {reviewing ? (
          <div>
            <div className="rounded-lg border border-line bg-canvas p-4">
              <div className="flex flex-wrap items-center gap-3 text-base font-semibold tabular">
                {existing && (
                  <>
                    <span className="text-ink-soft">{formatPay(existing.amount, existing.currency, existing.frequency)}</span>
                    <ArrowRight className="size-4 text-ink-faint" />
                  </>
                )}
                <span>{formatPay(amount, currency, frequency)}</span>
              </div>
              <p className="mt-2 text-sm text-ink-soft">Effective {date} · {reason.trim()}</p>
              {currencyChanged && (
                <p className="mt-2 text-sm text-warn">The pay currency changes from {existing!.currency} to {currency}. History keeps both values.</p>
              )}
            </div>
            {serverError && <div className="mt-3"><InlineAlert>{serverError}</InlineAlert></div>}
            <DialogFooter>
              <Button variant="secondary" onClick={() => setReviewing(false)} disabled={mutation.isPending}>
                Back
              </Button>
              <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
                {mutation.isPending ? "Saving…" : "Confirm change"}
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={review} noValidate className="space-y-4">
            {serverError && <InlineAlert>{serverError}</InlineAlert>}
            <div className="grid grid-cols-2 gap-3">
              <Field id="comp-currency" label="Currency" required>
                {(p) => (
                  <Select {...p} value={currency} onChange={(e) => { setCurrency(e.target.value as Currency); setConvertNote(null); }}>
                    {CURRENCY_LIST.map((c) => <option key={c}>{c}</option>)}
                  </Select>
                )}
              </Field>
              <Field id="comp-frequency" label="Pay frequency" required>
                {(p) => (
                  <Select {...p} value={frequency} onChange={(e) => setFrequency(e.target.value as Frequency)}>
                    <option value="annual">Annual</option>
                    <option value="monthly">Monthly</option>
                    <option value="hourly">Hourly</option>
                  </Select>
                )}
              </Field>
            </div>
            <Field id="comp-amount" label={`Amount (${currency} ${frequency === "annual" ? "per year" : frequency === "monthly" ? "per month" : "per hour"})`} error={errors.amount} required>
              {(p) => <Input {...p} inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />}
            </Field>
            {currencyChanged && (
              <div className="rounded-lg border border-line bg-canvas p-3 text-sm">
                <p className="text-ink-soft">
                  Currency is changing. Enter the new amount yourself, or start from the current salary converted at the latest rate.
                </p>
                <Button variant="secondary" size="sm" className="mt-2" onClick={() => convert.mutate()} disabled={convert.isPending}>
                  {convert.isPending ? "Converting…" : `Convert current amount to ${currency}`}
                </Button>
                {convertNote && <p className="mt-2 text-xs text-ink-faint">{convertNote}</p>}
              </div>
            )}
            <Field id="comp-date" label="Effective date" error={errors.effective_date} required>
              {(p) => <Input {...p} type="date" min={minDate} value={date} onChange={(e) => setDate(e.target.value)} />}
            </Field>
            <Field id="comp-reason" label="Reason" error={errors.reason} required>
              {(p) => <Textarea {...p} rows={2} maxLength={500} placeholder="e.g. Market adjustment" value={reason} onChange={(e) => setReason(e.target.value)} />}
            </Field>
            <DialogFooter>
              <Button variant="secondary" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button type="submit">Review change</Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
