import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search, TrendingUp, Wallet } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader, Pagination } from "@/components/common";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/form";
import { Table, TableWrap, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { CompensationDialog } from "@/features/compensation/CompensationDialog";
import { IncrementDialog } from "@/features/compensation/IncrementDialog";
import { STATUS_TONE } from "@/features/employees/EmployeeDirectory";
import { usePageMeta } from "@/hooks/page-meta";
import { useDebouncedValue } from "@/hooks/useDebounce";
import { useLookups } from "@/hooks/useLookups";
import { CURRENCY_LIST, formatDate, formatPay, STATUS_LABEL } from "@/lib/format";
import { compensationApi } from "@/services/endpoints";
import type { CompensationListItem } from "@/types/api";

export default function CompensationPage() {
  usePageMeta("Compensation", [{ label: "Compensation" }]);
  const lookups = useLookups();
  const [text, setText] = useState("");
  const q = useDebouncedValue(text.trim(), 300);
  const [currency, setCurrency] = useState("");
  const [dept, setDept] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [incrementFor, setIncrementFor] = useState<CompensationListItem | null>(null);
  const [updateFor, setUpdateFor] = useState<CompensationListItem | null>(null);

  const params = { q: q || undefined, currency: currency || undefined, department_id: dept || undefined, page, page_size: pageSize };
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["compensation", params],
    queryFn: () => compensationApi.list(params),
    placeholderData: keepPreviousData,
  });

  const reset = () => setPage(1);
  const asComp = (c: CompensationListItem) => ({
    id: c.id, employee_id: c.employee_id, amount: c.amount, currency: c.currency,
    frequency: c.frequency, effective_date: c.effective_date, updated_at: c.updated_at,
  });

  return (
    <>
      <PageHeader
        title="Compensation"
        description="Current pay for every employee. Apply increments or update pay; each change is added to the employee's salary history."
      />
      <Card>
        <div className="grid gap-3 border-b border-line p-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="sm:col-span-2">
            <Label htmlFor="comp-search">Search</Label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-faint" />
              <Input id="comp-search" type="search" className="pl-9" placeholder="Employee name or ID" value={text} onChange={(e) => { setText(e.target.value); reset(); }} />
            </div>
          </div>
          <div>
            <Label htmlFor="comp-dept">Department</Label>
            <Select id="comp-dept" value={dept} onChange={(e) => { setDept(e.target.value); reset(); }}>
              <option value="">All departments</option>
              {lookups.data?.departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </Select>
          </div>
          <div>
            <Label htmlFor="comp-currency">Currency</Label>
            <Select id="comp-currency" value={currency} onChange={(e) => { setCurrency(e.target.value); reset(); }}>
              <option value="">All currencies</option>
              {CURRENCY_LIST.map((c) => <option key={c}>{c}</option>)}
            </Select>
          </div>
        </div>

        {isLoading ? (
          <LoadingState label="Loading compensation…" />
        ) : isError && !data ? (
          <ErrorState error={error} onRetry={() => refetch()} title="Couldn't load compensation" />
        ) : data && data.items.length === 0 ? (
          <EmptyState title="No compensation records found" description="Adjust your search or filters." />
        ) : data ? (
          <>
            <TableWrap>
              <Table>
                <THead>
                  <tr>
                    <TH>Employee</TH>
                    <TH className="hidden md:table-cell">Department</TH>
                    <TH className="hidden lg:table-cell">Country</TH>
                    <TH className="text-right">Current pay</TH>
                    <TH className="hidden xl:table-cell">Effective</TH>
                    <TH className="text-right">Actions</TH>
                  </tr>
                </THead>
                <TBody>
                  {data.items.map((c) => {
                    const frozen = c.status === "terminated";
                    return (
                      <TR key={c.id}>
                        <TD>
                          <Link to={`/employees/${c.employee_id}`} className="font-medium hover:text-brand-600">{c.employee_name}</Link>
                          <div className="text-xs text-ink-faint">
                            <span className="tabular">{c.employee_code}</span>
                            {frozen && <Badge tone={STATUS_TONE[c.status]} className="ml-2">{STATUS_LABEL[c.status]}</Badge>}
                          </div>
                        </TD>
                        <TD className="hidden md:table-cell">{c.department}</TD>
                        <TD className="hidden lg:table-cell">{c.country}</TD>
                        <TD className="tabular whitespace-nowrap text-right font-medium">{formatPay(c.amount, c.currency, c.frequency)}</TD>
                        <TD className="tabular hidden whitespace-nowrap text-ink-soft xl:table-cell">{formatDate(c.effective_date)}</TD>
                        <TD>
                          <div className="flex justify-end gap-2">
                            <Button size="sm" disabled={frozen} onClick={() => setIncrementFor(c)} aria-label={`Apply increment for ${c.employee_name}`}>
                              <TrendingUp /> Increment
                            </Button>
                            <Button size="sm" variant="secondary" disabled={frozen} onClick={() => setUpdateFor(c)} aria-label={`Update pay for ${c.employee_name}`}>
                              <Wallet /> Update
                            </Button>
                          </div>
                        </TD>
                      </TR>
                    );
                  })}
                </TBody>
              </Table>
            </TableWrap>
            <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={pageSize} onPage={setPage} onPageSize={(n) => { setPageSize(n); reset(); }} />
          </>
        ) : null}
      </Card>

      {incrementFor && (
        <IncrementDialog open onOpenChange={(o) => !o && setIncrementFor(null)} compensation={asComp(incrementFor)} employeeName={incrementFor.employee_name} />
      )}
      {updateFor && (
        <CompensationDialog
          open
          onOpenChange={(o) => !o && setUpdateFor(null)}
          existing={asComp(updateFor)}
          employee={{ id: updateFor.employee_id, name: updateFor.employee_name, defaultCurrency: updateFor.currency, joiningDate: "" }}
        />
      )}
    </>
  );
}
