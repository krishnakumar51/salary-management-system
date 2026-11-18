import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { RateNote } from "@/components/common";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Card, CardHeader } from "@/components/ui/card";
import { Select } from "@/components/ui/form";
import { Table, TableWrap, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { AvgMedianBars, BandColumns, ChartCard, SERIES, SimpleLine } from "@/features/analytics/charts";
import { useLookups } from "@/hooks/useLookups";
import { useReportingCurrency } from "@/hooks/reporting-currency";
import { formatMoney, formatNumber } from "@/lib/format";
import { analyticsApi } from "@/services/endpoints";
import type { Currency, GroupStats } from "@/types/api";

/** min–max range with the interquartile box and median tick, on a shared scale. */
function RangeBar({ g, max }: { g: GroupStats; max: number }) {
  const pct = (v: string) => `${(Number(v) / max) * 100}%`;
  return (
    <div className="relative h-3 w-full min-w-40" role="img" aria-label={`Range ${g.minimum} to ${g.maximum}, median ${g.median}`}>
      <div className="absolute top-1/2 h-px -translate-y-1/2 bg-line-strong" style={{ left: pct(g.minimum), width: `calc(${pct(g.maximum)} - ${pct(g.minimum)})` }} />
      <div className="absolute top-0 h-3 rounded-sm" style={{ left: pct(g.p25), width: `calc(${pct(g.p75)} - ${pct(g.p25)})`, background: SERIES.blue, opacity: 0.35 }} />
      <div className="absolute top-[-2px] h-4 w-0.5" style={{ left: pct(g.median), background: SERIES.blue }} />
    </div>
  );
}

function GroupTable({ groups, currency, label }: { groups: GroupStats[]; currency: Currency; label: string }) {
  const max = Math.max(...groups.map((g) => Number(g.maximum)), 1);
  return (
    <TableWrap>
      <Table>
        <THead>
          <tr>
            <TH>{label}</TH>
            <TH className="text-right">Employees</TH>
            <TH className="text-right">Min</TH>
            <TH className="text-right">Median</TH>
            <TH className="text-right">Max</TH>
            <TH>Distribution (box = middle 50%)</TH>
          </tr>
        </THead>
        <TBody>
          {groups.map((g) => (
            <TR key={g.label}>
              <TD className="font-medium">{g.label}</TD>
              <TD className="tabular text-right">{formatNumber(g.count)}</TD>
              <TD className="tabular text-right">{formatMoney(g.minimum, currency, { compact: true })}</TD>
              <TD className="tabular text-right">{formatMoney(g.median, currency, { compact: true })}</TD>
              <TD className="tabular text-right">{formatMoney(g.maximum, currency, { compact: true })}</TD>
              <TD>
                <RangeBar g={g} max={max} />
              </TD>
            </TR>
          ))}
        </TBody>
      </Table>
    </TableWrap>
  );
}

function Section<T extends { rate_info: import("@/types/api").RateInfo }>({
  q,
  children,
}: {
  q: { data?: T; isLoading: boolean; isError: boolean; error: unknown; refetch: () => void };
  children: (d: T) => React.ReactNode;
}) {
  if (q.isLoading) return <LoadingState />;
  if (q.isError || !q.data) return <ErrorState error={q.error} onRetry={q.refetch} />;
  return <>{children(q.data)}</>;
}

export function AnalyticsView() {
  const { currency } = useReportingCurrency();
  const lookups = useLookups();
  const [dept, setDept] = useState("");
  const [country, setCountry] = useState("");

  const departments = useQuery({ queryKey: ["an-dept", currency], queryFn: () => analyticsApi.departments(currency) });
  const countries = useQuery({ queryKey: ["an-country", currency], queryFn: () => analyticsApi.countries(currency) });
  const distribution = useQuery({
    queryKey: ["an-dist", currency, dept, country],
    queryFn: () => analyticsApi.distribution(currency, { department_id: dept || undefined, country_id: country || undefined }),
  });
  const trends = useQuery({ queryKey: ["an-trends", currency], queryFn: () => analyticsApi.trends(currency) });
  const currencies = useQuery({ queryKey: ["an-cur", currency], queryFn: () => analyticsApi.currencies(currency) });

  const toBars = (g: GroupStats[]) => g.map((x) => ({ label: x.label, average: Number(x.average), median: Number(x.median) }));

  return (
    <div className="space-y-6">
      <RateNote info={departments.data?.rate_info} />

      <div className="grid gap-6 xl:grid-cols-2">
        <ChartCard title="Average vs median compensation by department" description={`Annualised, in ${currency}`}>
          <Section q={departments}>{(d) => (d.groups.length ? <AvgMedianBars data={toBars(d.groups)} currency={currency} /> : <EmptyState title="No data" />)}</Section>
        </ChartCard>
        <ChartCard title="Salary comparison across countries" description={`Average vs median, converted to ${currency}`}>
          <Section q={countries}>{(d) => (d.groups.length ? <AvgMedianBars data={toBars(d.groups)} currency={currency} /> : <EmptyState title="No data" />)}</Section>
        </ChartCard>
      </div>

      <Card>
        <CardHeader title="Salary distribution by department" description={`Min, median and max in ${currency}`} />
        <div className="mt-3">
          <Section q={departments}>{(d) => <GroupTable groups={d.groups} currency={currency} label="Department" />}</Section>
        </div>
      </Card>

      <Card>
        <CardHeader title="Salary distribution by country" description={`Min, median and max in ${currency}`} />
        <div className="mt-3">
          <Section q={countries}>{(d) => <GroupTable groups={d.groups} currency={currency} label="Country" />}</Section>
        </div>
      </Card>

      <ChartCard
        title="Employees by salary range"
        description={`Annual salary bands in ${currency}`}
        action={
          <div className="flex flex-wrap gap-2">
            <Select aria-label="Filter by department" className="h-8 w-44 py-0 text-xs" value={dept} onChange={(e) => setDept(e.target.value)}>
              <option value="">All departments</option>
              {lookups.data?.departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </Select>
            <Select aria-label="Filter by country" className="h-8 w-40 py-0 text-xs" value={country} onChange={(e) => setCountry(e.target.value)}>
              <option value="">All countries</option>
              {lookups.data?.countries.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </Select>
          </div>
        }
      >
        <Section q={distribution}>{(d) => <BandColumns data={d.bands} />}</Section>
      </ChartCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <ChartCard title="Compensation changes per month" description="Number of increments and updates per month, last 10 years (initial records excluded)">
          <Section q={trends}>
            {(d) =>
              d.points.length === 0 ? (
                <EmptyState title="No salary changes yet" />
              ) : (
                <SimpleLine name="Changes" data={d.points.map((p) => ({ label: p.month, value: p.changes }))} format={(v) => formatNumber(v)} />
              )
            }
          </Section>
        </ChartCard>
        <ChartCard title="Average increment size" description="Mean % increase per month">
          <Section q={trends}>
            {(d) =>
              d.points.length === 0 ? (
                <EmptyState title="No salary changes yet" />
              ) : (
                <SimpleLine
                  name="Average increment"
                  data={d.points.map((p) => ({ label: p.month, value: p.average_increment_percentage === null ? null : Number(p.average_increment_percentage) }))}
                  format={(v) => `${v.toFixed(2)}%`}
                  tickFormat={(v) => `${v}%`}
                />
              )
            }
          </Section>
        </ChartCard>
      </div>

      <Card>
        <CardHeader title="Compensation breakdown by currency" description="Original-currency totals alongside their converted value" />
        <div className="mt-3">
          <Section q={currencies}>
            {(d) => (
              <TableWrap>
                <Table>
                  <THead>
                    <tr>
                      <TH>Currency</TH>
                      <TH className="text-right">Employees</TH>
                      <TH className="text-right">Annual total (original)</TH>
                      <TH className="text-right">In {currency}</TH>
                    </tr>
                  </THead>
                  <TBody>
                    {d.items.map((t) => (
                      <TR key={t.currency}>
                        <TD className="font-medium">{t.currency}</TD>
                        <TD className="tabular text-right">{formatNumber(t.employee_count)}</TD>
                        <TD className="tabular text-right">{formatMoney(t.total_annual, t.currency)}</TD>
                        <TD className="tabular text-right">{formatMoney(t.total_annual_reporting, currency)}</TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </TableWrap>
            )}
          </Section>
        </div>
      </Card>
    </div>
  );
}
