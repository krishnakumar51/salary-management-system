import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, CalendarDays, Globe, Mail, Pencil, Phone, TrendingUp, UserX, Users, Wallet } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { ConfirmDialog, InlineAlert } from "@/components/common";
import { ErrorState, LoadingState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { CompensationDialog } from "@/features/compensation/CompensationDialog";
import { IncrementDialog } from "@/features/compensation/IncrementDialog";
import { SalaryHistory } from "@/features/compensation/SalaryHistory";
import { STATUS_TONE } from "@/features/employees/EmployeeDirectory";
import { usePageMeta } from "@/hooks/page-meta";
import { useReportingCurrency } from "@/hooks/reporting-currency";
import { EMPLOYMENT_LABEL, formatDate, formatMoney, FREQUENCY_LABEL, STATUS_LABEL } from "@/lib/format";
import { ApiError } from "@/services/api";
import { employeesApi, ratesApi } from "@/services/endpoints";

function Detail({ icon, label, children }: { icon: ReactNode; label: string; children: ReactNode }) {
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 text-ink-faint [&_svg]:size-4">{icon}</span>
      <div className="min-w-0">
        <dt className="text-xs text-ink-faint">{label}</dt>
        <dd className="mt-0.5 break-words text-sm text-ink">{children}</dd>
      </div>
    </div>
  );
}

export default function EmployeeProfilePage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const { currency: reporting } = useReportingCurrency();
  const { data: emp, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["employee", id],
    queryFn: () => employeesApi.get(id),
  });
  usePageMeta(emp?.full_name ?? "Employee", [{ label: "Employees", to: "/employees" }, { label: emp?.full_name ?? "…" }]);

  const [incrementOpen, setIncrementOpen] = useState(false);
  const [compOpen, setCompOpen] = useState(false);
  const [terminateOpen, setTerminateOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const comp = emp?.compensation ?? null;
  const converted = useQuery({
    queryKey: ["convert", comp?.amount, comp?.currency, comp?.frequency, reporting],
    queryFn: () => ratesApi.convert(comp!.amount, comp!.currency, reporting),
    enabled: !!comp && comp.currency !== reporting,
    staleTime: 60_000,
  });

  const terminate = useMutation({
    mutationFn: () => employeesApi.update(id, { status: "terminated" }),
    onSuccess: async () => {
      await qc.invalidateQueries();
      setTerminateOpen(false);
    },
    onError: (e) => {
      setActionError(e instanceof ApiError ? e.message : "Could not update status.");
      setTerminateOpen(false);
    },
  });

  if (isLoading) return <LoadingState label="Loading employee…" />;
  if (isError || !emp) {
    return (
      <Card>
        <ErrorState
          title={error instanceof ApiError && error.status === 404 ? "Employee not found" : "Couldn't load this employee"}
          error={error}
          onRetry={error instanceof ApiError && error.status === 404 ? undefined : () => refetch()}
        />
      </Card>
    );
  }

  const terminated = emp.status === "terminated";
  const annualFactor = comp ? { annual: 1, monthly: 12, hourly: 2080 }[comp.frequency] : 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-ink">{emp.full_name}</h1>
            <Badge tone={STATUS_TONE[emp.status]}>{STATUS_LABEL[emp.status]}</Badge>
          </div>
          <p className="mt-1 text-sm text-ink-soft">
            {emp.designation} · {emp.department.name} · <span className="tabular">{emp.employee_code}</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" asChild>
            <Link to={`/employees/${emp.id}/edit`}>
              <Pencil /> Edit
            </Link>
          </Button>
          {!terminated && (
            <Button variant="secondary" className="text-bad" onClick={() => setTerminateOpen(true)}>
              <UserX /> Terminate
            </Button>
          )}
        </div>
      </div>

      {actionError && <InlineAlert>{actionError}</InlineAlert>}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader title="Employee details" />
          <CardBody>
            <dl className="space-y-4">
              <Detail icon={<Mail />} label="Email">
                <a className="text-brand-600 hover:underline" href={`mailto:${emp.email}`}>
                  {emp.email}
                </a>
              </Detail>
              <Detail icon={<Phone />} label="Phone">
                {emp.phone ?? <span className="text-ink-faint">Not provided</span>}
              </Detail>
              <Detail icon={<Globe />} label="Country">
                {emp.country.name}
              </Detail>
              <Detail icon={<Building2 />} label="Department">
                {emp.department.name}
              </Detail>
              <Detail icon={<Users />} label="Employment type">
                {EMPLOYMENT_LABEL[emp.employment_type]}
              </Detail>
              <Detail icon={<CalendarDays />} label="Joining date">
                {formatDate(emp.joining_date)}
              </Detail>
              <Detail icon={<Users />} label="Manager">
                {emp.manager ? (
                  <Link className="text-brand-600 hover:underline" to={`/employees/${emp.manager.id}`}>
                    {emp.manager.full_name}
                  </Link>
                ) : (
                  <span className="text-ink-faint">None</span>
                )}
              </Detail>
            </dl>
          </CardBody>
        </Card>

        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader
              title="Current compensation"
              action={
                comp ? (
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" onClick={() => setIncrementOpen(true)} disabled={terminated}>
                      <TrendingUp /> Apply increment
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => setCompOpen(true)} disabled={terminated}>
                      <Wallet /> Update
                    </Button>
                  </div>
                ) : undefined
              }
            />
            <CardBody>
              {comp ? (
                <>
                  <p className="tabular text-3xl font-semibold tracking-tight text-ink">
                    {formatMoney(comp.amount, comp.currency, { decimals: comp.frequency === "hourly" ? 2 : 0 })}
                    <span className="ml-2 text-sm font-normal text-ink-soft">
                      {comp.currency} {FREQUENCY_LABEL[comp.frequency]}
                    </span>
                  </p>
                  <p className="mt-1 text-sm text-ink-faint">Effective {formatDate(comp.effective_date)}</p>
                  {comp.currency !== reporting && converted.data && (
                    <p className="tabular mt-3 text-sm text-ink-soft">
                      ≈ {formatMoney(converted.data.converted, reporting)} {FREQUENCY_LABEL[comp.frequency]} in {reporting}
                      {annualFactor !== 1 && (
                        <>
                          {" "}
                          (≈ {formatMoney(Number(converted.data.converted) * annualFactor, reporting)} per year)
                        </>
                      )}
                      <span className="block text-xs text-ink-faint">
                        Reporting view only · rate effective {formatDate(converted.data.effective_date)} · stored salary unchanged
                      </span>
                    </p>
                  )}
                  {terminated && <p className="mt-3 text-sm text-warn">Compensation is frozen for terminated employees.</p>}
                </>
              ) : (
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm text-ink-soft">No compensation has been recorded for this employee.</p>
                  {!terminated && (
                    <Button size="sm" onClick={() => setCompOpen(true)}>
                      <Wallet /> Add compensation
                    </Button>
                  )}
                </div>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Salary history" description="Every change is recorded permanently. Newest first." />
            <CardBody>
              <SalaryHistory employeeId={emp.id} />
            </CardBody>
          </Card>
        </div>
      </div>

      {comp && incrementOpen && (
        <IncrementDialog compensation={comp} employeeName={emp.full_name} open onOpenChange={setIncrementOpen} />
      )}
      {compOpen && (
        <CompensationDialog
          open
          onOpenChange={setCompOpen}
          existing={comp}
          employee={{
            id: emp.id,
            name: emp.full_name,
            defaultCurrency: emp.country.default_currency,
            joiningDate: emp.joining_date,
          }}
        />
      )}
      <ConfirmDialog
        open={terminateOpen}
        onOpenChange={setTerminateOpen}
        title={`Terminate ${emp.full_name}?`}
        description="The employee is marked as terminated and their compensation is frozen. Their record and salary history are kept."
        confirmLabel="Terminate employee"
        tone="danger"
        busy={terminate.isPending}
        onConfirm={() => terminate.mutate()}
      />
    </div>
  );
}
