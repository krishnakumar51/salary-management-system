import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, ArrowUpDown, FilterX, Plus, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { Pagination } from "@/components/common";
import { EmptyState, ErrorState, Skeleton } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/form";
import { Table, TableWrap, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { useDebouncedValue } from "@/hooks/useDebounce";
import { useLookups } from "@/hooks/useLookups";
import { useReportingCurrency } from "@/hooks/reporting-currency";
import { EMPLOYMENT_LABEL, formatDate, formatPay, STATUS_LABEL } from "@/lib/format";
import { employeesApi } from "@/services/endpoints";
import type { EmployeeQuery, EmployeeStatus } from "@/types/api";

type SortKey = EmployeeQuery["sort"];

export const STATUS_TONE: Record<EmployeeStatus, "ok" | "warn" | "neutral"> = {
  active: "ok",
  on_leave: "warn",
  terminated: "neutral",
};

const FILTER_KEYS = ["q", "department_id", "country_id", "designation", "status", "salary_min", "salary_max"] as const;

/** Text input that reports its value to the URL only after the user pauses typing. */
function DebouncedInput({
  value,
  onCommit,
  delay = 300,
  ...props
}: { value: string; onCommit: (v: string) => void; delay?: number } & Omit<
  React.InputHTMLAttributes<HTMLInputElement>,
  "value" | "onChange"
>) {
  const [text, setText] = useState(value);
  const debounced = useDebouncedValue(text, delay);
  // external changes (e.g. "Clear all filters") flow back into the box
  useEffect(() => setText(value), [value]);
  useEffect(() => {
    if (debounced !== value) onCommit(debounced);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);
  return <Input {...props} value={text} onChange={(e) => setText(e.target.value)} />;
}

function SortHeader({
  label,
  sortKey,
  current,
  order,
  onSort,
  className,
}: {
  label: string;
  sortKey: SortKey;
  current: SortKey;
  order: "asc" | "desc";
  onSort: (k: SortKey) => void;
  className?: string;
}) {
  const active = current === sortKey;
  const Icon = !active ? ArrowUpDown : order === "asc" ? ArrowUp : ArrowDown;
  return (
    <TH aria-sort={active ? (order === "asc" ? "ascending" : "descending") : "none"} className={className}>
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className="inline-flex items-center gap-1 uppercase tracking-wide hover:text-ink"
        aria-label={`Sort by ${label}`}
      >
        {label}
        <Icon className={`size-3.5 ${active ? "text-brand-600" : "opacity-60"}`} />
      </button>
    </TH>
  );
}

export function EmployeeDirectory() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const { currency } = useReportingCurrency();
  const lookups = useLookups();

  const get = (k: string) => params.get(k) ?? "";
  const sort = (get("sort") || "name") as SortKey;
  const order = (get("order") || "asc") as "asc" | "desc";
  const page = Math.max(1, Number(get("page")) || 1);
  const pageSize = [10, 25, 50, 100].includes(Number(get("page_size"))) ? Number(get("page_size")) : 25;

  const update = (patch: Record<string, string | null>, resetPage = true) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v === null || v === "") next.delete(k);
      else next.set(k, v);
    }
    if (resetPage) next.delete("page");
    setParams(next, { replace: true });
  };

  const query: EmployeeQuery = {
    q: get("q") || undefined,
    department_id: get("department_id") || undefined,
    country_id: get("country_id") || undefined,
    designation: get("designation") || undefined,
    status: get("status") || undefined,
    salary_min: get("salary_min") || undefined,
    salary_max: get("salary_max") || undefined,
    currency,
    sort,
    order,
    page,
    page_size: pageSize,
  };

  const { data, error, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ["employees", query],
    queryFn: () => employeesApi.list(query),
    placeholderData: keepPreviousData,
  });

  const activeFilters = FILTER_KEYS.filter((k) => get(k) !== "");
  const clearAll = () => {
    const next = new URLSearchParams(params);
    for (const k of [...FILTER_KEYS, "page"]) next.delete(k);
    setParams(next, { replace: true });
  };
  const onSort = (key: SortKey) => {
    if (key === sort) update({ order: order === "asc" ? "desc" : "asc" });
    else update({ sort: key, order: key === "joining_date" || key === "salary" ? "desc" : "asc" });
  };

  const L = lookups.data;

  return (
    <div>
      <Card>
        <div className="space-y-4 border-b border-line p-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="sm:col-span-2">
              <Label htmlFor="dir-search">Search</Label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-faint" />
                <DebouncedInput
                  id="dir-search"
                  type="search"
                  className="pl-9"
                  placeholder="Name, employee ID or email"
                  value={get("q")}
                  onCommit={(v) => update({ q: v.trim() })}
                />
              </div>
            </div>
            <div>
              <Label htmlFor="f-dept">Department</Label>
              <Select id="f-dept" value={get("department_id")} onChange={(e) => update({ department_id: e.target.value })}>
                <option value="">All departments</option>
                {L?.departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="f-country">Country</Label>
              <Select id="f-country" value={get("country_id")} onChange={(e) => update({ country_id: e.target.value })}>
                <option value="">All countries</option>
                {L?.countries.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="f-designation">Designation</Label>
              <Select id="f-designation" value={get("designation")} onChange={(e) => update({ designation: e.target.value })}>
                <option value="">All designations</option>
                {L?.designations.map((d) => (
                  <option key={d}>{d}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="f-status">Status</Label>
              <Select id="f-status" value={get("status")} onChange={(e) => update({ status: e.target.value })}>
                <option value="">All statuses</option>
                {L?.statuses.map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABEL[s]}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="f-min">Min annual salary ({currency})</Label>
              <DebouncedInput
                id="f-min"
                type="number"
                min={0}
                inputMode="numeric"
                placeholder="0"
                delay={500}
                value={get("salary_min")}
                onCommit={(v) => update({ salary_min: v })}
              />
            </div>
            <div>
              <Label htmlFor="f-max">Max annual salary ({currency})</Label>
              <DebouncedInput
                id="f-max"
                type="number"
                min={0}
                inputMode="numeric"
                placeholder="Any"
                delay={500}
                value={get("salary_max")}
                onCommit={(v) => update({ salary_max: v })}
              />
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-ink-faint">
              Salary filters and sorting compare annualised pay converted to {currency}.
            </p>
            {activeFilters.length > 0 && (
              <Button variant="ghost" size="sm" onClick={clearAll}>
                <FilterX /> Clear all filters ({activeFilters.length})
              </Button>
            )}
          </div>
        </div>

        {isError && !data ? (
          <ErrorState title="Couldn't load employees" error={error} onRetry={() => refetch()} />
        ) : isLoading ? (
          <div role="status" aria-label="Loading employees" className="divide-y divide-line">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-4 py-4">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="hidden h-4 w-32 sm:block" />
                <Skeleton className="ml-auto h-4 w-28" />
              </div>
            ))}
          </div>
        ) : data && data.items.length === 0 ? (
          <EmptyState
            title="No employees match your filters"
            description="Try a different search term or remove some filters."
            action={
              activeFilters.length > 0 ? (
                <Button variant="secondary" onClick={clearAll}>
                  <FilterX /> Clear all filters
                </Button>
              ) : (
                <Button asChild>
                  <Link to="/employees/new">
                    <Plus /> Add employee
                  </Link>
                </Button>
              )
            }
          />
        ) : data ? (
          <>
            {isError && (
              <div role="alert" className="border-b border-line bg-bad-bg px-4 py-2 text-sm text-bad">
                Couldn't refresh the list. Showing the last loaded results.{" "}
                <button className="underline" onClick={() => refetch()}>
                  Retry
                </button>
              </div>
            )}
            <TableWrap className={isFetching ? "opacity-70 transition-opacity" : "transition-opacity"}>
              <Table>
                <THead>
                  <tr>
                    <SortHeader label="Employee" sortKey="name" current={sort} order={order} onSort={onSort} />
                    <TH>Department</TH>
                    <TH className="hidden md:table-cell">Designation</TH>
                    <TH className="hidden lg:table-cell">Country</TH>
                    <TH>Status</TH>
                    <SortHeader label="Joined" sortKey="joining_date" current={sort} order={order} onSort={onSort} className="hidden xl:table-cell" />
                    <SortHeader label="Salary" sortKey="salary" current={sort} order={order} onSort={onSort} className="text-right" />
                  </tr>
                </THead>
                <TBody>
                  {data.items.map((e) => (
                    <TR key={e.id} className="cursor-pointer hover:bg-canvas/70" onClick={() => navigate(`/employees/${e.id}`)}>
                      <TD>
                        <Link
                          to={`/employees/${e.id}`}
                          className="font-medium text-ink hover:text-brand-600"
                          onClick={(ev) => ev.stopPropagation()}
                        >
                          {e.full_name}
                        </Link>
                        <div className="text-xs text-ink-faint">
                          <span className="tabular">{e.employee_code}</span> · {e.email}
                        </div>
                      </TD>
                      <TD>{e.department.name}</TD>
                      <TD className="hidden md:table-cell">
                        {e.designation}
                        <div className="text-xs text-ink-faint">{EMPLOYMENT_LABEL[e.employment_type]}</div>
                      </TD>
                      <TD className="hidden lg:table-cell">{e.country.name}</TD>
                      <TD>
                        <Badge tone={STATUS_TONE[e.status]}>{STATUS_LABEL[e.status]}</Badge>
                      </TD>
                      <TD className="tabular hidden whitespace-nowrap xl:table-cell">{formatDate(e.joining_date)}</TD>
                      <TD className="tabular whitespace-nowrap text-right font-medium">
                        {e.compensation ? (
                          formatPay(e.compensation.amount, e.compensation.currency, e.compensation.frequency)
                        ) : (
                          <span className="font-normal text-ink-faint">Not set</span>
                        )}
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </TableWrap>
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              pageSize={pageSize}
              onPage={(p) => update({ page: String(p) }, false)}
              onPageSize={(n) => update({ page_size: String(n) })}
            />
          </>
        ) : null}
      </Card>
    </div>
  );
}
