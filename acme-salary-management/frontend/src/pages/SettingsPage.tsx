import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { InlineAlert, PageHeader } from "@/components/common";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Field, Input, Select } from "@/components/ui/form";
import { Table, TableWrap, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { useAuth } from "@/hooks/auth";
import { usePageMeta } from "@/hooks/page-meta";
import { CURRENCY_LIST, formatDate, todayIso } from "@/lib/format";
import type { Errors } from "@/lib/validation";
import { ApiError } from "@/services/api";
import { ratesApi } from "@/services/endpoints";
import type { Currency } from "@/types/api";

function validate(v: { base: string; target: string; rate: string; date: string; source: string }): Errors {
  const e: Errors = {};
  if (v.base === v.target) e.target = "Must differ from the base currency";
  if (!/^\d+(\.\d{1,8})?$/.test(v.rate) || Number(v.rate) <= 0) e.rate = "Enter a positive rate with up to 8 decimals";
  if (!v.date) e.date = "Effective date is required";
  if (v.source.trim().length < 3) e.source = "Describe the source (at least 3 characters)";
  return e;
}

function ExchangeRates() {
  const qc = useQueryClient();
  const { data, isLoading, isError, error, refetch } = useQuery({ queryKey: ["rates"], queryFn: ratesApi.list });
  const [base, setBase] = useState<Currency>("USD");
  const [target, setTarget] = useState<Currency>("INR");
  const [rate, setRate] = useState("");
  const [date, setDate] = useState(todayIso());
  const [source, setSource] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const create = useMutation({
    mutationFn: () => ratesApi.create({ base_currency: base, target_currency: target, rate: rate.trim(), effective_date: date, source: source.trim() }),
    onSuccess: async () => {
      setRate(""); setSource(""); setSaved(true); setFormError(null);
      await qc.invalidateQueries();
    },
    onError: (err) => {
      setSaved(false);
      setFormError(err instanceof ApiError ? err.message : "Could not save the rate.");
    },
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const errs = validate({ base, target, rate, date, source });
    setErrors(errs);
    setSaved(false);
    if (Object.keys(errs).length === 0) create.mutate();
  };

  return (
    <Card>
      <CardHeader
        title="Exchange rates"
        description="Used only to convert salaries for reporting. Original salaries are never changed. The latest rate on or before today applies."
      />
      <CardBody className="space-y-6">
        <form onSubmit={submit} noValidate className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          {formError && <div className="sm:col-span-2 lg:col-span-6"><InlineAlert>{formError}</InlineAlert></div>}
          {saved && <div className="sm:col-span-2 lg:col-span-6"><InlineAlert tone="success">Exchange rate saved.</InlineAlert></div>}
          <Field id="rate-base" label="1 unit of">
            {(p) => <Select {...p} value={base} onChange={(e) => setBase(e.target.value as Currency)}>{CURRENCY_LIST.map((c) => <option key={c}>{c}</option>)}</Select>}
          </Field>
          <Field id="rate-target" label="equals (target)" error={errors.target}>
            {(p) => <Select {...p} value={target} onChange={(e) => setTarget(e.target.value as Currency)}>{CURRENCY_LIST.map((c) => <option key={c}>{c}</option>)}</Select>}
          </Field>
          <Field id="rate-value" label="Rate" error={errors.rate}>
            {(p) => <Input {...p} inputMode="decimal" placeholder="83.25" value={rate} onChange={(e) => setRate(e.target.value)} />}
          </Field>
          <Field id="rate-date" label="Effective date" error={errors.date}>
            {(p) => <Input {...p} type="date" value={date} onChange={(e) => setDate(e.target.value)} />}
          </Field>
          <Field id="rate-source" label="Source" error={errors.source} className="lg:col-span-2">
            {(p) => <Input {...p} placeholder="e.g. Treasury memo, 1 Jan" value={source} onChange={(e) => setSource(e.target.value)} />}
          </Field>
          <div className="sm:col-span-2 lg:col-span-6">
            <Button type="submit" disabled={create.isPending}>{create.isPending ? "Saving…" : "Add exchange rate"}</Button>
          </div>
        </form>

        {isLoading ? (
          <LoadingState />
        ) : isError ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : !data || data.length === 0 ? (
          <EmptyState title="No exchange rates configured" description="Add at least USD→INR and USD→EUR to enable conversion." />
        ) : (
          <TableWrap>
            <Table>
              <THead>
                <tr>
                  <TH>Pair</TH>
                  <TH className="text-right">Rate</TH>
                  <TH>Effective</TH>
                  <TH>Source</TH>
                </tr>
              </THead>
              <TBody>
                {data.map((r) => (
                  <TR key={r.id}>
                    <TD className="font-medium">1 {r.base_currency} → {r.target_currency}</TD>
                    <TD className="tabular text-right">{Number(r.rate).toLocaleString("en-US", { maximumFractionDigits: 8 })}</TD>
                    <TD className="tabular whitespace-nowrap">{formatDate(r.effective_date)}</TD>
                    <TD className="text-ink-soft">{r.source}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </TableWrap>
        )}
      </CardBody>
    </Card>
  );
}

export default function SettingsPage() {
  usePageMeta("Settings", [{ label: "Settings" }]);
  const { user } = useAuth();
  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Your account and the exchange rates used for reporting." />
      <Card>
        <CardHeader title="Your account" />
        <CardBody>
          <dl className="grid gap-4 sm:grid-cols-3 text-sm">
            <div><dt className="text-xs text-ink-faint">Name</dt><dd className="mt-0.5">{user?.full_name}</dd></div>
            <div><dt className="text-xs text-ink-faint">Email</dt><dd className="mt-0.5">{user?.email}</dd></div>
            <div><dt className="text-xs text-ink-faint">Role</dt><dd className="mt-0.5">HR Manager</dd></div>
          </dl>
        </CardBody>
      </Card>
      <ExchangeRates />
    </div>
  );
}
