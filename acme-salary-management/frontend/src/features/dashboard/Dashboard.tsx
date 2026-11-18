import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Banknote, Scale, UserCheck, Users } from "lucide-react";
import { Link } from "react-router-dom";

import { RateNote, StatCard } from "@/components/common";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Table, TableWrap, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { BandColumns, ChartCard, CountBars } from "@/features/analytics/charts";
import { useReportingCurrency } from "@/hooks/reporting-currency";
import { CHANGE_LABEL, formatDate, formatMoney, formatNumber, FREQUENCY_SHORT, STATUS_LABEL } from "@/lib/format";
import { analyticsApi } from "@/services/endpoints";
import type { EmployeeStatus } from "@/types/api";

export function Dashboard() {
  const { currency } = useReportingCurrency();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["dashboard", currency],
    queryFn: () => analyticsApi.dashboard(currency),
  });

  if (isLoading) return <LoadingState label="Loading dashboard…" />;
  if (isError || !data) return <Card><ErrorState error={error} onRetry={() => refetch()} title="Couldn't load the dashboard" /></Card>;

  const d = data;
  const money = (v: string) => formatMoney(v, currency);
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total employees" value={formatNumber(d.total_employees)} icon={<Users />} hint={`${formatNumber(d.employees_without_compensation)} without compensation`} />
        <StatCard
          label="Active employees"
          value={formatNumber(d.active_employees)}
          icon={<UserCheck />}
          hint={`${d.total_employees ? Math.round((d.active_employees / d.total_employees) * 100) : 0}% of workforce`}
        />
        <StatCard label={`Average salary (${currency})`} value={money(d.overall.average)} icon={<Banknote />} hint="Annualised, non-terminated" />
        <StatCard label={`Median salary (${currency})`} value={money(d.overall.median)} icon={<Scale />} hint={`Range ${formatMoney(d.overall.minimum, currency, { compact: true })} – ${formatMoney(d.overall.maximum, currency, { compact: true })}`} />
      </div>
      <RateNote info={d.rate_info} />

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Employees by country" description="Headcount, all statuses">
          <CountBars data={d.by_country} />
        </ChartCard>
        <ChartCard title="Employees by department" description="Headcount, all statuses">
          <CountBars data={d.by_department} />
        </ChartCard>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader title="Employment status" />
          <CardBody>
            <ul className="space-y-3">
              {d.by_status.map((s) => (
                <li key={s.label} className="flex items-center justify-between text-sm">
                  <Badge tone={s.label === "active" ? "ok" : s.label === "on_leave" ? "warn" : "neutral"}>
                    {STATUS_LABEL[s.label as EmployeeStatus] ?? s.label}
                  </Badge>
                  <span className="tabular font-medium">{formatNumber(s.count)}</span>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
        <div className="lg:col-span-2">
          <ChartCard title="Salary distribution" description={`Employees per annual salary band (${currency})`}>
            <BandColumns data={d.salary_bands} />
          </ChartCard>
        </div>
      </div>

      <Card>
        <CardHeader
          title="Total compensation by currency"
          description="Original currencies are never summed together. The last column converts each to the reporting currency."
        />
        <TableWrap className="mt-3">
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
              {d.totals_by_currency.map((t) => (
                <TR key={t.currency}>
                  <TD className="font-medium">{t.currency}</TD>
                  <TD className="tabular text-right">{formatNumber(t.employee_count)}</TD>
                  <TD className="tabular text-right">{formatMoney(t.total_annual, t.currency)}</TD>
                  <TD className="tabular text-right">{money(t.total_annual_reporting)}</TD>
                </TR>
              ))}
              <TR className="bg-canvas/60">
                <TD className="font-semibold">Total</TD>
                <TD />
                <TD />
                <TD className="tabular text-right font-semibold">{money(d.total_compensation_reporting)}</TD>
              </TR>
            </TBody>
          </Table>
        </TableWrap>
      </Card>

      <Card>
        <CardHeader title="Highest and lowest salary by department" description={`Annualised, converted to ${currency}. Compared within a department, never across currencies unconverted.`} />
        <TableWrap className="mt-3">
          <Table>
            <THead>
              <tr>
                <TH>Department</TH>
                <TH className="text-right">Employees</TH>
                <TH className="text-right">Lowest</TH>
                <TH className="text-right">Median</TH>
                <TH className="text-right">Highest</TH>
              </tr>
            </THead>
            <TBody>
              {d.department_extremes.map((g) => (
                <TR key={g.label}>
                  <TD className="font-medium">{g.label}</TD>
                  <TD className="tabular text-right">{formatNumber(g.count)}</TD>
                  <TD className="tabular text-right">{money(g.minimum)}</TD>
                  <TD className="tabular text-right">{money(g.median)}</TD>
                  <TD className="tabular text-right">{money(g.maximum)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </TableWrap>
      </Card>

      <Card>
        <CardHeader
          title="Recent salary changes"
          action={
            <Link to="/compensation" className="inline-flex items-center gap-1 text-sm text-brand-600 hover:underline">
              Manage compensation <ArrowRight className="size-3.5" />
            </Link>
          }
        />
        {d.recent_changes.length === 0 ? (
          <EmptyState title="No salary changes yet" description="Increments and updates will appear here." />
        ) : (
          <TableWrap className="mt-3">
            <Table>
              <THead>
                <tr>
                  <TH>Employee</TH>
                  <TH>Change</TH>
                  <TH className="text-right">New salary</TH>
                  <TH className="text-right">Effective</TH>
                </tr>
              </THead>
              <TBody>
                {d.recent_changes.map((c) => (
                  <TR key={c.id}>
                    <TD>
                      <Link to={`/employees/${c.employee_id}`} className="font-medium hover:text-brand-600">
                        {c.employee_name}
                      </Link>
                      <div className="text-xs text-ink-faint">{c.employee_code}</div>
                    </TD>
                    <TD>
                      {CHANGE_LABEL[c.change_type] ?? c.change_type}
                      {c.increment_percentage && (
                        <Badge tone="ok" className="ml-2">
                          +{Number(c.increment_percentage).toLocaleString("en-US", { maximumFractionDigits: 2 })}%
                        </Badge>
                      )}
                    </TD>
                    <TD className="tabular text-right">
                      {formatMoney(c.new_amount, c.new_currency, { decimals: c.new_frequency === "hourly" ? 2 : 0 })} {FREQUENCY_SHORT[c.new_frequency]}
                    </TD>
                    <TD className="tabular whitespace-nowrap text-right text-ink-soft">{formatDate(c.effective_date)}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </TableWrap>
        )}
      </Card>
    </div>
  );
}
